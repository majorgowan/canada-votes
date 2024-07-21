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
from zipfile import ZipFile
from constants import datadir, provcodes


def write_json(obj, filename, **json_args):
    """
    Write the

    Parameters
    ----------
    obj : json-serializable object
        object to be written as json
    filename : str
        name of file to write
    **json_args
        kwargs for json.dump function

    Returns
    -------
    None
    """
    if not filename.lower().endswith(".json"):
        filename = f"{filename}.json"
    with open(filename, "w") as jsf:
        json.dump(obj, jsf)


def generate_riding_map_file(province="ON", overwrite=False):
    """
    Generate a json file mapping riding names (e.g. "Thornhill")
    to riding numbers (35104)

    Parameters
    ----------
    province : str
        two-letter abbreviation
    overwrite : bool
        if True, overwrite existing file

    Returns
    -------
    str
        name of created file
    """
    riding_map = dict()
    provcode = provcodes[province]

    filename = os.path.join(datadir,
                            f"{province}_{provcode}_ridings_map")

    if not overwrite and os.path.exists(filename):
        print(f"{filename} exists")
        return

    votesfile = os.path.join(datadir,
                             f"pollresults_resultatsbureau{provcode}.zip")
    print(votesfile)

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

    write_json(riding_map, filename, indent=2, sort_keys=True)


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

        # load geodataframe
        gdf = gpd.read_file(os.path.join(datadir, adv_file))

        for prov, provcode in provcodes.items():
            # iterate over provinces, generate subset dataframe
            # and write it to zip file
            gdf_prov = (gdf[gdf["FED_NUM"]
                        .astype(str).str.startswith(f"{provcode}")]
                        .to_crs(epsg=4326))

            prov_filename = f"{prov}_{provcode}_{suffix}"
            if os.path.exists(os.path.join(datadir,
                                           f"{prov_filename}.zip")):
                print(f"file {prov_filename} already exists, skipping... ")
                continue

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