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
from .constants import datadir, provcodes, areas


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


def update_riding_map_file(province):
    """
    Generate a json file mapping riding names (e.g. "Thornhill")
    to riding numbers (35104)

    Parameters
    ----------
    province : str
        two-letter abbreviation

    Returns
    -------
    str
        name of created file
    """
    # if riding_map file exists, load it
    riding_map_file = os.path.join(datadir, "riding_map.json")
    if os.path.exists(riding_map_file):
        riding_map = load_json(riding_map_file)
    else:
        riding_map = dict()

    provcode = provcodes[province]

    votesfile = os.path.join(datadir,
                             f"pollresults_resultatsbureau{provcode}.zip")

    if not os.path.exists(votesfile):
        print("Please first download votes file with get_vote_data()")
        return

    with ZipFile(votesfile, "r") as zf:
        for fname in zf.namelist():
            # iterate over CSV files in the zip and extract
            # riding names and numbers from first line
            if re.match(r"pollresults.*csv", fname):
                temp_df = pd.read_csv(zf.open(fname))
                riding_number, riding_name = temp_df.iloc[0, :2].values
                riding_map[riding_name] = int(riding_number)

    # write updated riding_map back to disk
    write_json(riding_map, riding_map_file, indent=2, sort_keys=True)


def get_riding_map():
    """
    Load riding map from disk

    Returns
    -------
    dict
    """
    return load_json(os.path.join(datadir, "riding_map.json"))


def get_inv_riding_map():
    """
    Load inverse riding map

    Returns
    -------
    dict
    """
    riding_map = get_riding_map()
    return {v: k for k, v in riding_map.items()}


def provs_from_ridings(ridings):
    """
    get list of province numeric codes from list of riding names

    Parameters
    ----------
    ridings : list
        riding names

    Returns
    -------
    list
        province codes
    """
    riding_map = get_riding_map()
    provcode_list = []
    riding_codes = []
    for rid in ridings:
        riding_codes.append(riding_map[rid])
        provcode = int(str(riding_map[rid])[:2])
        if provcode not in provcode_list:
            provcode_list.append(provcode)
    return provcode_list


def apply_riding_map(ridings=None, area=None):
    """
    convert list of riding names or area to list of riding numbers

    Parameters
    ----------
    ridings : list
        riding names
    area : str
        name of predefined area

    Returns
    -------
    list
    """
    riding_map = get_riding_map()
    if ridings is None:
        if area is None:
            return []
        ridings = areas[area]

    return [riding_map[rid] for rid in ridings]


def generate_provincial_geometries():
    """
    Split the country-wide file into province files (to save memory).
    """
    eday_file = "PD_CA_2021_EN.zip"
    adv_file = "ADVPD_CA_2021_EN.zip"
    if not os.path.exists(os.path.join(datadir, eday_file)):
        print(f"please download shape file {eday_file} with get_geometries()")
        return
    if not os.path.exists(os.path.join(datadir, adv_file)):
        print(f"please download shape file {adv_file} with get_geometries()")
        return

    for gdffile, suffix in [(eday_file, "geometries"),
                            (adv_file, "geometries_adv")]:
        # load GeoDataFrame
        gdf = gpd.read_file(os.path.join(datadir, gdffile))

        for prov, provcode in provcodes.items():
            # iterate over provinces, generate subset dataframe
            # and write it to zip file
            prov_filename = f"{prov}_{provcode}_{suffix}"
            if os.path.exists(os.path.join(datadir,
                                           f"{prov_filename}.zip")):
                print(f"file {prov_filename} already exists, skipping... ")
                continue

            gdf_prov = (gdf[gdf["FED_NUM"]
                        .astype(str).str.startswith(f"{provcode}")]
                        .to_crs(epsg=4326))

            # make folder for shape files
            os.mkdir(os.path.join(datadir, prov_filename))
            gdf_prov.to_file(os.path.join(datadir,
                                          prov_filename,
                                          f"{prov_filename}.shp"))

            # add folder to zip file and delete
            with ZipFile(os.path.join(datadir, f"{prov_filename}.zip"),
                         "w") as zf:
                for f in os.listdir(os.path.join(datadir, prov_filename)):
                    zf.write(os.path.join(datadir, prov_filename, f),
                             arcname=f)
            shutil.rmtree(os.path.join(datadir, prov_filename))


def compute_riding_centroids():
    """
    Generate CSV file with riding numbers, names and centroids (in lon/lat)
    """
    adv_file = "ADVPD_CA_2021_EN.zip"
    if not os.path.exists(os.path.join(datadir, adv_file)):
        print(f"please download shape file {adv_file} with get_geometries()")
        return

    # load GeoDataFrame
    gdf = gpd.read_file(os.path.join(datadir, adv_file))
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

    inv_riding_map = get_inv_riding_map()
    gdf["DistrictName"] = gdf.index.map(inv_riding_map)

    # write to CSV file
    (gdf
     .reset_index()
     .get(["FED_NUM", "DistrictName", "centroid_lon", "centroid_lat"])
     .to_csv(os.path.join(datadir, "riding_centroids.csv"), index=None))


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


def get_nearest_ridings(riding, n=10):
    """
    Get list of nearest ridings to given riding (by centroid distance)

    Parameters
    ----------
    riding : str
        name of riding
    n : int
        number of ridings to return

    Returns
    -------
    list
        names of nearest ridings
    """
    if not os.path.exists(os.path.join(datadir, "riding_centroids.csv")):
        compute_riding_centroids()

    df_centroids = pd.read_csv(os.path.join(datadir, "riding_centroids.csv"))

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


def validate_ridings(ridings):
    """
    check that list of riding names exist

    Parameters
    ----------
    ridings : list
        names of ridings

    Returns
    -------
    list
        invalid riding names
    """
    ridings_map = get_riding_map()

    invalid_ridings = [rid for rid in ridings
                       if rid not in ridings_map]

    return invalid_ridings


def query_ridings(pattern):
    """

    Parameters
    ----------
    pattern : str
        regex pattern to query list of riding names

    Returns
    -------
    list
        matching riding names
    """
    ridings_map = get_riding_map()

    pattern = r"" + pattern
    matches = [rid for rid in ridings_map
               if re.match(pattern, rid)]
    return matches
