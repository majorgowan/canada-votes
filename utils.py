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
import pandas as pd
from zipfile import ZipFile
from .constants import datadir, provcodes, areas, votes_encodings


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

    csv_encoding = votes_encodings.get(year, "utf-8")

    with ZipFile(votesfile, "r") as zf:
        for fname in zf.namelist():
            # iterate over CSV files in the zip and extract
            # riding names and numbers from first line
            if re.match(r"pollresults.*csv", fname):
                temp_df = pd.read_csv(zf.open(fname), encoding=csv_encoding)
                riding_number, riding_name = temp_df.iloc[0, :2].values
                # for some crazy reason, in 2008, riding names end in " (?!)
                riding_name = riding_name.strip("\"")
                riding_map[riding_name] = int(riding_number)

    # write updated riding_map back to disk
    write_json(riding_map, riding_map_file, ensure_ascii=False,
               indent=2, sort_keys=True)


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
    Convert area to list of riding numbers in a given year

    Parameters
    ----------
    area : str
        name of predefined area
    year : int or list
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


def party_difference(gdf_vote, plot_variable, party1, party2):
    """
    Given a GeoDataFrame with multiindex including "Party", return
    single-party frame with "Difference" column representing the difference
    between the two parties in terms of specified plot variable

    Parameters
    ----------
    gdf_vote : GeoDataFrame
        with data for plot_variable and two parties
    plot_variable : str
        name of column to compare
    party1 : str
        name of first party to compare
    party2 : str
        name of second party to compare

    Returns
    -------
    GeoDataFrame
        including "Difference" column
    """

    # select the subsets for the two parties
    gdf1 = (gdf_vote
            .xs(level="Party", key=party1)
            .copy())

    gdf2 = (gdf_vote
            .xs(level="Party", key=party2)
            .copy())

    # check if indexes of the two party tables match (it won't if one
    # or the other party is not represented in some locations, in which case
    # the subtraction of the plot_variable will fail)
    if not gdf1.index.equals(gdf2.index):
        # compute a common index and apply it to each frame
        index_union = gdf1.index.union(gdf2.index)
        gdf1 = gdf1.reindex(index_union)
        gdf2 = gdf2.reindex(index_union)

        # fill the missing values of the plot_variable column with zeros
        gdf1[plot_variable] = gdf1[plot_variable].fillna(0)
        gdf2[plot_variable] = gdf2[plot_variable].fillna(0)

        # fill the missing geometries with the values from the other party
        gdf1["geometry"] = gdf1["geometry"].fillna(gdf2["geometry"])

    # cmopute the difference and Bob should be your uncle
    gdf1["Difference"] = gdf1[plot_variable] - gdf2[plot_variable]

    return gdf1
