"""
-------------------------------------------------------
Utility functions for canadavotes project
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
import re
import os
import json
import shutil
import pandas as pd
import geopandas as gpd
from math import cos, pi
from zipfile import ZipFile
from .constants import datadir, provcodes, areas, geometry_files


def get_int_part(s):
    """

    Parameters
    ----------
    s : str
        containing integer part

    Returns
    -------
    int
    """
    mch = re.match(r"[a-zA-Z]*[0-9]+", s.strip())
    if mch is not None:
        return int(mch[0])
    return None


def write_json(obj, filename, **json_args):
    """
    Write the

    Parameters
    ----------
    obj : json-serializable
        object to be written as json
    filename : str
        name of file to write
    **json_args
        kwargs for json.dump() function

    Returns
    -------
    None
    """
    if not filename.lower().endswith(".json"):
        filename = f"{filename}.json"
    with open(filename, "w") as jsf:
        json.dump(obj, jsf, **json_args)


def load_json(filepath):
    """
    Load a json file to an object

    Parameters
    ----------
    filepath : str
        path to json file to load

    Returns
    -------
    object
        serialized in json file
    """
    if not filepath.lower().endswith(".json"):
        filepath = f"{filepath}.json"

    with open(filepath, "r") as jsf:
        json_obj = json.load(jsf)

    return json_obj


def update_riding_map_file(province, year):
    """
    Generate a json file mapping riding names (e.g. "Thornhill")
    to riding numbers (35104)

    Parameters
    ----------
    province : str
        two-letter abbreviation
    year : int
        election year

    Returns
    -------
    str
        name of created file
    """
    # if riding_map file exists, load it
    riding_map_file = os.path.join(datadir, f"{year}_riding_map.json")
    if os.path.exists(riding_map_file):
        riding_map = load_json(riding_map_file)
    else:
        riding_map = dict()

    provcode = provcodes[province]

    votesfile = os.path.join(
        datadir, f"{year}_pollresults_resultatsbureau{provcode}.zip")

    if not os.path.exists(votesfile):
        print("Please first download votes file with get_vote_data()")
        return

    with ZipFile(votesfile, "r") as zf:
        for fname in zf.namelist():
            # iterate over CSV files in the zip and extract
            # riding names and numbers from first line
            if re.match(r"pollresults.*csv", fname):
                temp_df = pd.read_csv(zf.open(fname), encoding="latin1")
                riding_number, riding_name = temp_df.iloc[0, :2].values
                # for some crazy reason, in 2008, riding names end in " (?!)
                riding_name = riding_name.strip("\"")
                riding_map[riding_name] = int(riding_number)

    # write updated riding_map back to disk
    write_json(riding_map, riding_map_file, indent=2, sort_keys=True)


def get_riding_map(year):
    """
    Load riding map from disk

    Parameters
    ----------
    year : int
        election year for which to obtain map

    Returns
    -------
    dict
    """
    return load_json(os.path.join(datadir, f"{year}_riding_map.json"))


def get_inv_riding_map(year):
    """
    Load inverse riding map

    Parameters
    ----------
    year : int
        election year

    Returns
    -------
    dict
    """
    riding_map = get_riding_map(year)
    return {v: k for k, v in riding_map.items()}


def provs_from_ridings(year, ridings):
    """
    get list of province numeric codes from list of riding names

    Parameters
    ----------
    year : int
        election year
    ridings : list
        riding names

    Returns
    -------
    list
        province codes
    """
    riding_map = get_riding_map(year)
    provcode_list = []
    riding_codes = []
    for rid in ridings:
        riding_codes.append(riding_map[rid])
        provcode = int(str(riding_map[rid])[:2])
        if provcode not in provcode_list:
            provcode_list.append(provcode)
    return provcode_list


def area_to_ridings(area, year):
    """
    Convert area to list of ridings in a given year

    Parameters
    ----------
    area : str
        name of predefined area
    year : int
        election year

    Returns
    -------
    list
        ridings names
    """
    all_ridings = areas[area]
    ridings = apply_riding_map(year, all_ridings)
    return ridings


def apply_riding_map(year, ridings=None):
    """
    convert list of riding names or area to list of riding numbers

    Parameters
    ----------
    year : int
        election year
    ridings : list
        riding names

    Returns
    -------
    list
    """
    riding_map = get_riding_map(year)
    return [riding_map[rid] for rid in ridings]


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
    layer = filedata["layer"]

    if not os.path.exists(os.path.join(datadir, eday_file)):
        print(f"please download shape file {eday_file} with get_geometries()")
        return

    # load GeoDataFrame
    gdf = gpd.read_file(os.path.join(datadir, eday_file),
                        layer=layer, encoding="latin1")

    # for some reason, in 2019 columns were "FEDNUM" etc. but in 2015
    # and 2021 they are "FED_NUM" etc.
    if "FEDNUM" in gdf.columns:
        gdf = gdf.rename(columns={"FEDNUM": "FED_NUM",
                                  "PDNUM": "PD_NUM",
                                  "ADVPOLLNUM": "ADV_POLL_N",
                                  "ADVPDNUM": "ADV_POLL_N"})
    if "ADV_POLL" in gdf.columns:
        gdf = gdf.rename(columns={"ADV_POLL": "ADV_POLL_N"})
    if "ADVPOLL" in gdf.columns:
        gdf = gdf.rename(columns={"ADVPOLL": "ADV_POLL_N"})

    for prov, provcode in provcodes.items():
        # iterate over provinces, generate subset dataframe
        # and write it to zip file
        eday_filename = f"{year}_{prov}_{provcode}_geometries"
        adv_filename = f"{year}_{prov}_{provcode}_geometries_adv"
        if os.path.exists(os.path.join(datadir,
                                       f"{eday_filename}.zip")):
            print(f"file {eday_filename} already exists, skipping... ")
            continue

        # restrict national file to this province and convert to lon/lat
        gdf_prov = (gdf[gdf["FED_NUM"]
                    .astype(str).str.startswith(f"{provcode}")])

        # for recent elections, separate Advance Poll geometries file
        # published, but we can "dissolve" it from the election-day
        # file anyway:
        gdf_prov_adv = (gdf_prov
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
    layer = filedata["layer"]

    if not os.path.exists(os.path.join(datadir, filename)):
        print(f"please download shape file {filename} with get_geometries()")
        return

    # load GeoDataFrame
    gdf = gpd.read_file(os.path.join(datadir, filename),
                        layer=layer, encoding="latin1")
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
        compute_riding_centroids(year)

    df_centroids = pd.read_csv(os.path.join(datadir,
                                            f"{year}_riding_centroids.csv"),
                               encoding="latin1")

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


def validate_ridings(ridings, year=2021):
    """
    check that list of riding names exist

    Parameters
    ----------
    ridings : list
        names of ridings
    year : int
        election year

    Returns
    -------
    list
        valid ridings
    """
    ridings_map = get_riding_map(year)

    return [rid for rid in ridings if rid in ridings_map]


def query_ridings(pattern, year=2021):
    """

    Parameters
    ----------
    pattern : str
        regex pattern to query list of riding names
    year : int
        election year

    Returns
    -------
    list
        matching riding names
    """
    ridings_map = get_riding_map(year)

    pattern = r"" + pattern
    matches = [rid for rid in ridings_map
               if re.match(pattern, rid)]
    return matches
