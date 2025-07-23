"""
-------------------------------------------------------
Routines for processing Ontario provincial election data
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
import os
import pandas as pd
import geopandas as gpd
from zipfile import ZipFile
from .constants import datadir
from .utils import get_int_part


def load_ontario_vote_data(year, ridings=None):
    """
    Load previously downloaded ontario data, extract csv files from
    zips and do some processing

    Parameters
    ----------
    year : int
        one of 2018, 2022
    ridings : list
        names of ridings to load

    Returns
    -------
    dict
        various DataFrames pertaining to the election
    """
    with (ZipFile(os.path.join(datadir,
                               f"{year}_Ontario_General_Election-csv.zip"))
          as zf):
        cand_file = [f for f in zf.namelist() if "Valid Votes" in f][0]
        official_return_file = [f for f in zf.namelist()
                                if "Official Return" in f][0]
        pol_interest_file = [f for f in zf.namelist()
                             if "Political Interest" in f][0]
        with zf.open(cand_file, "r") as cf:
            df_candidates = pd.read_csv(cf)
        with zf.open(pol_interest_file, "r") as pif:
            df_interest = pd.read_csv(pif)
        with zf.open(official_return_file, "r") as orf:
            df_votes = pd.read_csv(orf)

    # drop BiElection rows
    df_interest = df_interest.loc[~df_interest["EventNameEnglish"]
                                  .str.contains("By-elections")]
    df_candidates = df_candidates.loc[~df_candidates["EventNameEnglish"]
                                      .str.contains("By-elections")]
    df_votes = df_votes.loc[~df_votes["EventNameEnglish"]
                            .str.contains("By-elections")]

    # drop French columns
    df_interest = (
        df_interest
        .drop([col for col in df_interest.columns
               if "French" in col], axis=1)
        .rename(columns={"PoliticalInterestCode": "PartyCode",
                         "PartyFullNameEnglish": "Party"})
    )
    df_candidates = (
        df_candidates
        .drop([col for col in df_candidates.columns
               if "French" in col], axis=1)
        .rename(columns={"ElectoralDistrictNameEnglish": "DistrictName",
                         "ElectoralDistricNumber": "DistrictNumber",
                         "NameOfCandidates": "Candidate",
                         "PoliticalInterestCode": "PartyCode"})
    )
    df_votes = (
        df_votes
        .drop([col for col in df_votes.columns
               if "French" in col], axis=1)
        .rename(columns={"EventNameEnglish": "EventName",
                         "ElectoralDistrictNameEnglish": "DistrictName",
                         "NameOfCandidates": "Candidate"})
    )
    # replace em-dashes (seriously?!) with double dashes and remove
    # leading district number from votes table
    df_candidates["DistrictName"] = (df_candidates["DistrictName"]
                                     .map(lambda s: s.replace("—", "--")))
    df_votes["DistrictName"] = (df_votes["DistrictName"]
                                .map(lambda s: s[4:].replace("—", "--")))

    # restrict data to selected ridings
    if ridings is not None:
        df_candidates = df_candidates[df_candidates["DistrictName"]
                                      .isin(ridings)]
        df_votes = df_votes[df_votes["DistrictName"]
                            .isin(ridings)]

    # merge party names into candidate file
    df_candidates = df_candidates.merge(df_interest[["PartyCode", "Party"]],
                                        on="PartyCode", how="left")
    # replace "NaN" / "NoAffiliation" with "IND" / "Independent"
    df_candidates.loc[df_candidates["PartyCode"].isna(),
                      "Party"] = "Independent"
    df_candidates.loc[df_candidates["PartyCode"].isna(),
                      "PartyCode"] = "IND"

    # distinguish value in Party column where multiple Independent candidates
    # appear in same riding (N.B. sometimes it's called "No Affiliation")
    df_indep_cands = (df_candidates.loc[df_candidates["Party"]
                                        == "Independent",
                                        ["DistrictName", "Candidate"]]
                      .drop_duplicates())
    cand_rename_map = {}
    for district_name, grp in df_indep_cands.groupby("DistrictName"):
        ind_counter = 0
        grp_unique = grp[["Candidate"]].drop_duplicates()
        if len(grp_unique) > 1:
            for irow, row in grp_unique.iterrows():
                ind_counter += 1
                cand_rename_map[row["Candidate"]] = (
                    f"Independent-{ind_counter:02d}"
                )
    for cand, party_str in cand_rename_map.items():
        df_candidates.loc[df_candidates["Candidate"] == cand,
                          "Party"] = party_str

    # make numeric poll-number column
    df_votes["PD_NUM"] = 0
    df_votes.loc[~df_votes["PollNumber"].str.contains("ADV"),
                 "PD_NUM"] = (
        df_votes.loc[~df_votes["PollNumber"].str.contains("ADV"),
                     "PollNumber"]
        .map(lambda s: get_int_part(s))
    )

    return {
        "candidates": df_candidates,
        "votes": df_votes
    }


def load_ontario_geometries(year, ridings=None):
    """
    Load and process shapefile with polling division boundaries

    Parameters
    ----------
    year : int
        one of 2018, 2022
    ridings : list
        names of ridings to load

    Returns
    -------
    gpd.GeoDataFrame
    """

    zipname = os.path.join(datadir,
                           f"{year}_Ontario_Polling_Division_Shapefile.zip")

    # get folder name inside zip file
    with ZipFile(zipname) as zf:
        folder_name = zf.namelist()[0].split("/")[0]

    # now read shapefile
    gdf = gpd.read_file(f"{zipname}!{folder_name}", encoding="latin-1")

    # drop French columns
    gdf = (
        gdf
        .drop([col for col in gdf.columns
               if "_FR" in col], axis=1)
        .rename(columns={"ED_NAME_EN": "DistrictName",
                         "ED_ID": "DistrictNumber",
                         "PD_NUMBER": "PD_NUM"})
    )

    # replace em-dashes with double dashes
    gdf["DistrictName"] = (gdf["DistrictName"]
                           .map(lambda s: s.replace("—", "--")))


    # filter by riding list
    if ridings is not None:
        gdf = gdf[gdf["DistrictName"].isin(ridings)]

    return gdf


def make_candidate_map(df_candidates):
    """
    Convert candidates DataFrame into a map from district number to
    party to candidate name

    Parameters
    ----------
    df_candidates : pd.DataFrame

    Returns
    -------
    dict
    """
    candidate_map = {}
    for dist_num, grp in df_candidates.groupby("DistrictNumber"):
        candidate_map[dist_num] = {}
        for party, candidate_row in grp.set_index("Party").iterrows():
            candidate_map[dist_num][party] = candidate_row["Candidate"]

    return candidate_map