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
from itertools import combinations
from .constants import datadir, provcodes, votes_encodings


def get_int_part(s):
    """
    Given a string, extract the first integer (if any)

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


def find_merge_sets(df_vote):
    """
    Find all the poll division (numeric part only) that are merged together
    (e.g. if poll divisions "18A" and "23B" are both MergedWith "17C", all
    three of 18, 23 and 17 should belong to the same "merge set" and be
    dissolved together, including divisions "18B", "23A" etc.)

    Parameters
    ----------
    df_vote : DataFrame or GeoDataFrame
        with columns "DistrictNumber", "Poll" and "MergedWith"

    Returns
    -------
    dict
        mapping DistrictNumber to list of sets of polls to merge
    """
    def extract_merge_pair(row):
        pollnum = get_int_part(row["Poll"])
        mwnum = get_int_part(row["MergedWith"])
        if pollnum is None or mwnum is None:
            return None
        return mwnum, pollnum

    def compute_merge_sets(merge_pairs):
        merge_sets = []
        for merge_pair in merge_pairs:
            flag = 0
            # check if the first poll in the pair is in an existing set
            for merge_set in merge_sets:
                if merge_pair[0] in merge_set:
                    merge_set.add(merge_pair[1])
                    flag = 1
                    break
            # if first poll not in an existing set, creat new set
            if flag == 0:
                merge_sets.append(set(merge_pair))

        # go through the merge sets two at a time and if any
        # overlap, merge them (then start over and repeat until
        # none overlap)
        no_overlaps = False
        while not no_overlaps:
            overlaps_flag = False
            for combo in combinations(merge_sets, 2):
                if not combo[0].isdisjoint(combo[1]):
                    # remove the overlapping sets and append their union
                    merge_sets.remove(combo[0])
                    merge_sets.remove(combo[1])
                    merge_sets.append(combo[0].union(combo[1]))
                    # found an overlap so break out and start again
                    overlaps_flag = True
                    break
            if not overlaps_flag:
                no_overlaps = True

        return merge_sets

    srs_mp = (df_vote
              .dropna(subset="MergedWith")
              .groupby("DistrictNumber")
              .apply(lambda grp: grp.apply(extract_merge_pair,
                                           axis=1).sort_values().unique(),
                     include_groups=False))

    merge_sets_dict = {}
    for district, mp_array in srs_mp.items():
        merge_sets_dict[district] = compute_merge_sets(mp_array)

    return merge_sets_dict


def make_merge_map(df_eday, merge_sets_dict):
    """
    Construct mapping from district numbers to poll numbers to the merge-sets
    they belong to (usually a singleton set), denoted by a string of the
    form "FEDNUM_PDNUM" or "FEDNUM_MERGE_MERGEGRPNUM"

    Parameters
    ----------
    df_eday : pd.DataFrame
        with DistrictNumber, Poll, PD_NUM and MergedWith columns
    merge_sets_dict : dict
        mapping district number to list of sets of polls to be merged
        (see find_merge_sets() function)

    Returns
    -------
    dict
    """
    merge_map = {}
    for fed_num in df_eday["DistrictNumber"].unique():
        merge_map[fed_num] = {
            pd_num: f"{fed_num}_{pd_num}" for pd_num
            in df_eday.loc[df_eday["DistrictNumber"] == fed_num,
            "PD_NUM"].unique()
        }
        if fed_num in merge_sets_dict:
            merge_sets = merge_sets_dict[fed_num]
            for iset, merge_set in enumerate(merge_sets):
                for pd_num in merge_set:
                    merge_map[fed_num][pd_num] = f"{fed_num}_merge_{iset:03d}"

    return merge_map


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


def add_eday_votes(vdf_eday, vdf_adv, gdf):
    """
    Build a mapping from election-day polling division to advance polling
    division (which is in the geometry tables) and use it to add election-day
    votes corresponding to each advance poll division

    Parameters
    ----------
    vdf_eday : pd.DataFrame
        election-day votes table
    vdf_adv : pd.DataFrame
        advance votes table
    gdf : gpd.GeoDataFrame
        election-day geometry table

    Returns
    -------
    pd.DataFrame
        advance-poll votes table with column for election-day votes
    """
    # mapping from election-day to advance poll numbers
    eday_to_advance_dict = {}
    for fed_num, grp in gdf[["FED_NUM", "PD_NUM",
                             "ADV_POLL_N"]].groupby("FED_NUM"):
        eday_to_advance_dict[fed_num] = (grp.set_index("PD_NUM")
                                         .apply(lambda row: row["ADV_POLL_N"],
                                                axis=1)
                                         .to_dict())
    # convert the mapping to a series with same index as eday dataframe
    vdf_eday_adv_poll_n_srs = (
        vdf_eday
        .apply(lambda row: (eday_to_advance_dict.get(row["DistrictNumber"], {})
                            .get(row["PD_NUM"], 0)),
               axis=1)
    )

    # sum election-day votes for each advance-poll division
    vdf_adv["ElectionDayVotes"] = vdf_adv.apply(
        lambda row: vdf_eday.loc[(vdf_eday["DistrictNumber"]
                                  == row["DistrictNumber"])
                                 & (vdf_eday_adv_poll_n_srs == row["PD_NUM"])
                                 & (vdf_eday["Party"] == row["Party"]),
                                 "Votes"].sum(),
        axis=1
    )
    vdf_adv["TotalVotes"] = vdf_adv["Votes"] + vdf_adv["ElectionDayVotes"]

    return vdf_adv
