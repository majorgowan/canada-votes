"""
-------------------------------------------------------
Routines for reading and manipulating geometry files
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
import os
import shutil
import pandas as pd
import geopandas as gpd
from math import cos, pi
from zipfile import ZipFile
from shapely.errors import GEOSException
from shapely import (MultiPolygon, Polygon, unary_union, coverage_union_all,
                     simplify)
from .votes import compute_vote_fraction
from .constants import codeprovs, datadir, areas, geometry_files, provcodes
from .utils import (provs_from_ridings, validate_ridings, apply_riding_map,
                    get_inv_riding_map, find_merge_sets)


def load_geometries(ridings=None, area=None, year=2021, advance=False):
    """
    load geopandas file and select subset of ridings

    Parameters
    ----------
    ridings : list
        names of ridings to select
    area : str
        name of predefined block of ridings
    year : int
        election year for which to load data
    advance : bool
        if True, load geometries for advance polls

    Returns
    -------
    gpd.GeoDataFrame
        dataframe with geometries
    """
    if ridings is None:
        if area is not None:
            ridings = areas[area]
        else:
            print("please specify list of ridings or name of area")
            return

    # select only valid ridings
    ridings = validate_ridings(ridings, year)

    riding_codes = apply_riding_map(year=year, ridings=ridings)

    # get list of province codes from riding numbers
    provcode_list = provs_from_ridings(year=year, ridings=ridings)

    gdf = gpd.GeoDataFrame()

    for provcode in provcode_list:
        province = codeprovs[provcode]

        if advance:
            geometry_file = f"{year}_{province}_{provcode}_geometries_adv.zip"
        else:
            geometry_file = f"{year}_{province}_{provcode}_geometries.zip"

        gdf0 = gpd.read_file(os.path.join(datadir, geometry_file),
                             encoding="latin1")
        gdf = pd.concat((gdf, gdf0), ignore_index=True)

    gdf = gdf[gdf["FED_NUM"].isin(riding_codes)]

    # some poll areas have multiple rows (when they consist of
    # multiple disjoint parts) ... do a robust dissolve on those
    # N.B. keep the first row of the other columns, noting the
    # other GIS columns will no longer be correct (but we don't use them)
    pd_num_col = "ADV_POLL_N" if advance else "PD_NUM"

    # find polls with multiple rows
    multirow_polls = (gdf.loc[gdf[["FED_NUM", pd_num_col]].duplicated(),
                              ["FED_NUM", pd_num_col]]
                      .drop_duplicates()
                      .apply(lambda row: tuple(row.values), axis=1))
    gdf_multirow = (gdf
                    .set_index(["FED_NUM", pd_num_col])
                    .loc[multirow_polls]
                    .reset_index())
    # dissolve geometries of rows with same (FED_NUM, PD_NUM)
    gdf_multirow = robust_dissolve(gdf_multirow,
                                   by=["FED_NUM", pd_num_col],
                                   aggfunc={ccol: (lambda col: col.iloc[0])
                                            for ccol in gdf_multirow.columns
                                            if ccol not in ("geometry",
                                                            "FED_NUM",
                                                            pd_num_col)})
    # drop the rows from the original dataframe
    gdf = (gdf
           .set_index(["FED_NUM", pd_num_col])
           .drop(gdf_multirow.index))
    # append the dissolved dataframe
    gdf = (pd.concat((gdf, gdf_multirow))
           .sort_index()
           .reset_index())

    # change poll number and advance poll number to integer type
    if "PD_NUM" in gdf.columns:
        gdf["PD_NUM"] = gdf["PD_NUM"].astype("int64")
    gdf["ADV_POLL_N"] = gdf["ADV_POLL_N"].astype("int64")

    return gdf


def dissolve_ridings(gdf, robust=True):
    """
    combine polling station zones to whole ridings

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        dataframe with "geometries" and "FED_NUM" columns
    robust : bool
        if True, use custom robust_dissolve() function

    Returns
    -------
    gpd.GeoDataFrame
        dataframe with dissolved geometries
    """
    # join polygons of boundaries in each riding
    if robust:
        gdf = robust_dissolve(gdf, by="FED_NUM")
    else:
        gdf = gdf.dissolve(by="FED_NUM", method="coverage")

    # switch coordinate system to extract centroid, then switch back
    gdf = gdf.to_crs(epsg=2263)
    gdf["centroid"] = gdf.centroid
    # switch back to longitude/latitude
    gdf = gdf.to_crs(epsg=4326)
    gdf["centroid"] = gdf["centroid"].to_crs(epsg=4326)

    return gdf


def merge_votes(gdf, df_vote):
    """
    Merge election results into a GeoDataFrame

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        geometry data
    df_vote : pd.DataFrame
        votes data

    Returns
    -------
    gpd.GeoDataFrame
        geometry data with merged votes data
    """
    # detect whether geometry data is for advance poll
    if "PD_NUM" in gdf.columns:
        advance = False
    else:
        advance = True

    if not advance:
        # merge votes to geodataframe on the numeric part of the Poll
        gdf = gdf.merge(df_vote,
                        left_on=["FED_NUM", "PD_NUM"],
                        right_on=["DistrictNumber", "PD_NUM"],
                        how="left")

    else:
        # merge votes to geodataframe on the Advance Poll number
        gdf = gdf.merge(df_vote,
                        left_on=["FED_NUM", "ADV_POLL_N"],
                        right_on=["DistrictNumber", "PD_NUM"],
                        how="left")
        # set index to conform to election-day format
        # gdf = gdf.set_index(["DistrictName", "Party", "Poll"])

    return gdf


def combine_mergedwith(gdf):
    """
    In some cases multiple poll divisions are counted together, denoted
    by a non-missing "MergedWith" column in df_vote

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        with merged vote data

    Returns
    -------
    gpd.GeoDataFrame
    """
    # since we're writing new columns, don't touch passed-in DataFrame
    gdf = gdf.copy()

    # plan is to dissolve polling stations
    # grouped by common vote-counting merges

    # this is to handle a bug in some riding vote files where the
    # rows for the different parties at the same poll
    # have different "MergedWith" values (some NaN, some non-NaN)
    # the code below will set the MergedWith value to the majority
    # value within each poll
    def grpfun(grp):
        grp = grp.copy()
        grpmode = grp["MergedWith"].mode()
        if len(grpmode) > 0:
            grp["MergedWith"] = grpmode.iloc[0]
        return grp
    gdf = (gdf
           .groupby(["DistrictName", "PD_NUM"], as_index=False)[gdf.columns]
           .apply(grpfun))

    # compute the "merge sets", i.e. groups of polls that all merge to the
    # same target poll number (N.B. if there are multiple polls with the same
    # number in the votes file -- e.g. 17A and 17B -- and any are involved
    # in a merge, all of them are grouped in the same merge set.  The
    # boundary files don't do A's and B's.  What choice # did I have?
    merge_sets = find_merge_sets(gdf)

    # construct the aggregation function for each column to apply on dissolve
    # compose poll string consisting of all merged polls
    aggfunc_poll = {"Poll": lambda col: ", ".join(col.str.strip().values)}
    # add the votes together (usually only one will be nonzero)
    aggfunc_sum = {col: "sum" for col in
                   ["Votes", "TotalVotes", "Electors", "RejectedBallots"]}
    # for other columns, take the first value in the group after sorting
    # by votes (this will take one of the merge-target values)
    aggfunc_first = {col: lambda col: col.iloc[0] for col
                     in gdf.columns if col not in
                     ["geometry", "Poll", "Party"] + list(aggfunc_sum.keys())}
    # final aggregation function dict
    aggfunc = {**aggfunc_poll, **aggfunc_sum, **aggfunc_first}

    # iterate over the merge sets, popping the rows involved, dissolving
    # them into a single row, and concat them back onto the dataframe
    dissolved_dfs = []
    if len(merge_sets) > 0:
        for fednum, merge_set_list in merge_sets.items():
            for merge_set in merge_set_list:
                popset = gdf.index[(gdf["FED_NUM"] == fednum)
                                   & (gdf["PD_NUM"].isin(merge_set))]

                df_diss = (robust_dissolve(gdf.loc[popset]
                                          .sort_values(["Party", "Votes"],
                                                       ascending=False),
                                          by="Party", aggfunc=aggfunc)
                           .reset_index())
                # remove popped rows
                gdf = gdf.drop(popset, axis=0)
                # save dissolved dataframe
                dissolved_dfs.append(df_diss)
        # concat the dissolved dataframes to the remaining original
        gdf = pd.concat([gdf] + dissolved_dfs, ignore_index=True)
        gdf = gdf.sort_values(["FED_NUM", "PD_NUM", "Party"])

        # (re)compute vote fraction with aggregated columns
        gdf = compute_vote_fraction(gdf)

        # set index to usual form
        gdf = gdf.set_index(["DistrictName", "Party", "PD_NUM"])

    return gdf


def robust_dissolve(gdf, by=None, aggfunc=None, verbose=False):
    """
    Robust (hopefully) alternative to GeoDataFrame.dissolve() for
    merging geometries within a grouping based on another column

    Parameters
    ----------
    gdf : gpd.GeoDataFrame or pd.DataFrame
        table to dissolve
    by : str or list
        name of column or list of columns on which to groupby
    aggfunc : dict
        functions to apply to non-grouping columns
    verbose : bool
        print out warnings when exceptions thrown

    Returns
    -------
    gpd.GeoDataFrame
        dissolved dataframe
    """
    def colfun(col):
        """
        function to apply to the geometry column in each group, implementing
        different approaches to merging geometries

        Parameters
        ----------
        col : gpd.GeoSeries

        Returns
        -------
        gpd.GeoSeries
        """
        try:
            # try coverage dissolve (fastest if it works)
            return coverage_union_all(col)
        except GEOSException as ge:
            try:
                if verbose:
                    print("Warning: coverage union failed,"
                          + " trying unary dissolve"
                          + f"\n{ge}")
                # try unary dissolve (might also fail)
                return unary_union(col)
            except GEOSException as ge2:
                # try building a multipolygon
                try:
                    if verbose:
                        print("Warning: unary dissolve failed,"
                              + " trying manually building MultiPolygon"
                              + f"\n{ge2}")
                    # handle simple and nonsimple geometries separately
                    simps = unary_union(col[col.is_simple])
                    if isinstance(simps, MultiPolygon):
                        simps = list(simps.geoms)
                    else:
                        simps = [simps]
                    nonsimps = col[~col.is_simple].tolist()
                    # if isinstance(nonsimps, MultiPolygon):
                    #     nonsimps = list(nonsimps.geoms)
                    # else:
                    #     nonsimps = [nonsimps]
                    return MultiPolygon(simps + nonsimps)
                except GEOSException as ge3:
                    if verbose:
                        print("Warning: MultiPolygon failed,"
                              + " trying simplifying geometries and"
                              + " then unary dissolve"
                              + f"\n{ge3}")
                    # try simplifying polygons and dissolving again
                    col = simplify(col, tolerance=0.001)
                    try:
                        return unary_union(col)
                    except GEOSException as ge4:
                        # try other method
                        print(f"Warning: unary dissolve failed again,"
                              + " trying coverage union"
                              + f"\n{ge4}")
                        return coverage_union_all(col)

    # add colfun to the aggfunc dict passed in
    if aggfunc is None:
        aggfunc = {}
    aggfunc["geometry"] = colfun
    gdf = gdf.groupby(by=by).agg(aggfunc)
    # make sure new "geometry" column is the geometry column of record
    gdf = gdf.set_geometry("geometry", crs="epsg:4326")
    return gdf


def generate_provincial_geometries(year=2021):
    """
    Split the country-wide file into province files (to save memory).

    Parameters
    ----------
    year : int
        year for which to generate provincial geometry files
    """
    filedata = geometry_files.get(year, None)
    if filedata is None:
        print(f"year {year} not implemented")
        return None

    eday_file = filedata["filename"]
    layers = filedata["layers"]

    if not os.path.exists(os.path.join(datadir, eday_file)):
        print(f"please download shape file {eday_file} with get_geometries()")
        return

    # load GeoDataFrame
    if layers is not None:
        gdf_areas = gpd.read_file(os.path.join(datadir, eday_file),
                                  layer=layers["areas"],
                                  encoding="latin1")
        gdf_points = gpd.read_file(os.path.join(datadir, eday_file),
                                   layer=layers["points"],
                                   encoding="latin1")
        # set PD type to T ("triangle")
        gdf_points["PD_TYPE"] = "T"
        # convert geometry column from points to polygons (triangles)
        gdf_points["geometry"] = (
            gdf_points["geometry"]
            .map(lambda mp: point_to_triangle(mp.geoms[0], delta=200))
        )
        gdf = pd.concat((gdf_areas, gdf_points), ignore_index=True)
    else:
        gdf = gpd.read_file(os.path.join(datadir, eday_file),
                            encoding="latin1")

    # for some reason, in 2019 columns were "FEDNUM" etc. but in 2015
    # and 2021 they are "FED_NUM" etc.
    if "FEDNUM" in gdf.columns:
        gdf = gdf.rename(columns={"FEDNUM": "FED_NUM",
                                  "PDNUM": "PD_NUM",
                                  "PDTYPE": "PD_TYPE",
                                  "ADVPOLLNUM": "ADV_POLL_N",
                                  "ADVPDNUM": "ADV_POLL_N"})
    if "ADV_POLL" in gdf.columns:
        gdf = gdf.rename(columns={"ADV_POLL": "ADV_POLL_N"})
    if "ADVPOLL" in gdf.columns:
        gdf = gdf.rename(columns={"ADVPOLL": "ADV_POLL_N"})

    # sort by riding and poll number
    gdf = gdf.sort_values(["FED_NUM", "PD_NUM"])

    for prov, provcode in provcodes.items():
        # iterate over provinces, generate subset dataframe
        # and write it to zip file
        eday_filename = f"{year}_{prov}_{provcode}_geometries"
        adv_filename = f"{year}_{prov}_{provcode}_geometries_adv"
        if os.path.exists(os.path.join(datadir, f"{eday_filename}.zip")):
            print(f"file {eday_filename} already exists, skipping... ")
            continue

        # restrict national file to this province and convert to lon/lat
        gdf_prov = (gdf[gdf["FED_NUM"]
                    .astype(str).str.startswith(f"{provcode}")])

        # for recent elections, separate Advance Poll geometries file
        # published, but we can "dissolve" it from the election-day
        # file anyway (only use normal PD_TYPE):
        gdf_prov_adv = (gdf_prov[gdf_prov["PD_TYPE"] != "T"]
                        .sort_values(["FED_NUM", "ADV_POLL_N"])
                        .dissolve(by=["FED_NUM", "ADV_POLL_N"])
                        .reset_index()
                        .get(["FED_NUM", "ADV_POLL_N", "geometry"]))

        # write both election-day and advance-poll shape files to disk:
        for gdf_p, filename in [(gdf_prov, eday_filename),
                                (gdf_prov_adv, adv_filename)]:
            # make folder for shape files
            os.mkdir(os.path.join(datadir, filename))
            # convert to longitude / latitude coordinates
            # and write to disk
            (gdf_p
             .to_crs(epsg=4326)
             .to_file(os.path.join(datadir, filename, f"{filename}.shp")))

            # add folder to zip file and delete
            with ZipFile(os.path.join(datadir, f"{filename}.zip"),
                         "w") as zf:
                for f in os.listdir(os.path.join(datadir, filename)):
                    zf.write(os.path.join(datadir, filename, f),
                             arcname=f)
            shutil.rmtree(os.path.join(datadir, filename))


def compute_riding_centroids(year):
    """
    Generate CSV file with riding numbers, names and centroids (in lon/lat)

    Parameters
    ----------
    year : int
        election year
    """
    filedata = geometry_files[year]
    filename = filedata["filename"]
    layers = filedata["layers"]

    if not os.path.exists(os.path.join(datadir, filename)):
        print(f"please download shape file {filename} with get_geometries()")
        return

    # load GeoDataFrame
    if layers is not None:
        layer = layers["areas"]
    else:
        layer = None
    gdf = gpd.read_file(os.path.join(datadir, filename),
                        layer=layer, encoding="latin1")

    # 2019 file has column "FEDNUM" instead of "FED_NUM"
    if "FEDNUM" in gdf.columns:
        gdf = gdf.rename(columns={"FEDNUM": "FED_NUM"})

    # dissolve ridings
    gdf = gdf.dissolve(by="FED_NUM")

    # switch coordinate system to extract centroid, then switch back
    gdf = gdf.to_crs(epsg=2263)
    gdf["centroid"] = gdf.centroid
    # switch back to longitude/latitude
    gdf = gdf.to_crs(epsg=4326)
    gdf["centroid"] = gdf["centroid"].to_crs(epsg=4326)

    gdf["centroid_lon"] = gdf["centroid"].x
    gdf["centroid_lat"] = gdf["centroid"].y

    inv_riding_map = get_inv_riding_map(year)
    gdf["DistrictName"] = gdf.index.map(inv_riding_map)

    # write to CSV file
    (gdf
     .reset_index()
     .get(["FED_NUM", "DistrictName", "centroid_lon", "centroid_lat"])
     .to_csv(os.path.join(datadir, f"{year}_riding_centroids.csv"),
             index=None))


def haversine(p1, p2):
    """
    Compute haversine distance argument between two points

    Parameters
    ----------
    p1 : (float, float)
        first point in (longitude, latitude) degrees
    p2 : (float, float)
        second point

    Returns
    -------
    float
        2 * ( sin( d / (2 R) ) ) ^2
    """
    p1 = pi / 180. * p1[0], pi / 180. * p1[1]
    p2 = pi / 180. * p2[0], pi / 180. * p2[1]
    dlat = p2[1] - p1[1]
    dlon = p2[0] - p1[0]
    return 1.0 - cos(dlat) + cos(p1[1]) * cos(p2[1]) * (1.0 - cos(dlon))


def point_to_triangle(point, delta=200):
    """
    Construct triangle around the first point in a Point

    Parameters
    ----------
    point : shapely.Point object
        the point around which to build the triangle
    delta : float
        the width of the base of the triangle (in metres?)

    Returns
    -------
    shapely.Polygon object
    """
    return Polygon(shell=[(point.x - 0.5 * delta, point.y - 0.5 * delta),
                          (point.x + 0.5 * delta, point.y - 0.5 * delta),
                          (point.x, point.y + 0.5 * delta)])


def get_nearest_ridings(riding, n=10, year=2021):
    """
    Get list of nearest ridings to given riding (by centroid distance)

    Parameters
    ----------
    riding : str
        name of riding
    n : int
        number of ridings to return
    year : int
        election year

    Returns
    -------
    list
        names of nearest ridings
    """
    if not os.path.exists(os.path.join(datadir,
                                       f"{year}_riding_centroids.csv")):
        print("computing and caching riding centroids . . .")
        compute_riding_centroids(year)

    df_centroids = pd.read_csv(os.path.join(datadir,
                                            f"{year}_riding_centroids.csv"),
                               encoding="utf-8")

    if (df_centroids["DistrictName"] == riding).sum() == 0:
        return []

    p1 = (df_centroids
          .loc[df_centroids["DistrictName"] == riding]
          .get(["centroid_lon", "centroid_lat"])
          .iloc[0]
          .values)

    dists = (df_centroids
             .apply(lambda row: haversine(p1,
                                          row[["centroid_lon",
                                               "centroid_lat"]].values),
                    axis=1)
             .sort_values())
    return df_centroids.loc[dists.index[:n], "DistrictName"].tolist()
