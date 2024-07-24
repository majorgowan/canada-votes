"""
-------------------------------------------------------
Routines for reading and manipulating geometry files
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
import os
import pandas as pd
import geopandas as gpd
from .votes import compute_vote_fraction
from .constants import codeprovs, datadir, areas
from .utils import provs_from_ridings, apply_riding_map, get_int_part


def load_geometries(ridings=None, area=None, advance=False):
    """
    load geopandas file and select subset of ridings

    Parameters
    ----------
    ridings : list
        names of ridings to select
    area : str
        name of predefined block of ridings
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
    riding_codes = apply_riding_map(ridings)

    # get list of province codes from riding numbers
    provcode_list = provs_from_ridings(ridings)

    gdf = gpd.GeoDataFrame()

    for provcode in provcode_list:
        province = codeprovs[provcode]

        if advance:
            geometry_file = f"{province}_{provcode}_geometries_adv.zip"
        else:
            geometry_file = f"{province}_{provcode}_geometries.zip"

        gdf0 = gpd.read_file(os.path.join(datadir, geometry_file))
        gdf = pd.concat((gdf, gdf0), ignore_index=True)

    gdf = gdf[gdf["FED_NUM"].isin(riding_codes)]

    # change poll number and advance poll number to integer type
    if "PD_NUM" in gdf.columns:
        gdf["PD_NUM"] = gdf["PD_NUM"].astype("int64")
    gdf["ADV_POLL_N"] = gdf["ADV_POLL_N"].astype("int64")

    return gdf


def dissolve_ridings(gdf):
    """
    combine polling station zones to whole ridings

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        dataframe with "geometries" and "FED_NUM" columns

    Returns
    -------
    gpd.GeoDataFrame
        dataframe with dissolved geometries
    """
    # join polygons of boundaries in each riding
    gdf = gdf.dissolve(by="FED_NUM")

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
        gdf = gdf.set_index(["DistrictName", "Party", "ADV_POLL_N"])

    return gdf


def combine_mergedwith_columns(gdf):
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

    # dissolve polling stations with votes merged
    # if a poll is not merged with another,
    # then it is "merged" with itself
    gdf["MergedWith"] = [row["Poll"].strip()
                         if pd.isna(row["MergedWith"])
                         else row["MergedWith"]
                         for _, row in gdf.iterrows()]

    # reassign "PD_NUM" to numeric part of "MergedWith" column
    # (old PD_NUM disappears on dissolve below anyway)
    gdf["PD_NUM"] = gdf["MergedWith"].map(get_int_part)

    # create geometry for groups of merged polls
    # the number of votes should only be non-zero for the target
    # of the merge
    gdf = gdf.dissolve(by=["DistrictName", "Party", "PD_NUM"],
                       aggfunc={"Electors": "sum",
                                "Votes": "max",
                                "TotalVotes": "max"})

    # (re)compute vote fraction with aggregated columns
    gdf = compute_vote_fraction(gdf)

    return gdf
