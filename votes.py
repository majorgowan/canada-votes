"""
-------------------------------------------------------
Routines for reading and manipulating votes files
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
import os
import re
import pandas as pd
from zipfile import ZipFile
from .constants import datadir, provcodes, codeprovs, votes_encodings, areas
from .utils import get_int_part, apply_riding_map, validate_ridings


def load_vote_data_prov(year, province, ridings=None):
    """
    Load dataframe with vote results from single province

    Parameters
    ----------
    year : int
        election year from which to load votes
    province : str
        two character province abbreviation
    ridings : list
        ridings to load

    Returns
    -------
    pd.DataFrame
    """
    provcode = provcodes[province]
    votesfile = os.path.join(datadir,
                             f"{year}_pollresults_resultatsbureau{provcode}"
                             + ".zip")

    df = pd.DataFrame()

    if ridings is not None:
        ridings = validate_ridings(ridings, year)
        riding_nos = [str(rid) for rid in apply_riding_map(year, ridings)]
    else:
        riding_nos = []

    french_columns = [
        "Electoral District Name_French/Nom de circonscription_Français",
        "Political Affiliation Name_French/Appartenance politique_Français"
    ]
    dtype_map = {
        "Merge With/Fusionné avec": "str",
        "Polling Station Number/Numéro du bureau de scrutin": "str"
    }
    # note below apparent repeated keys have different apostrophe characters
    # (to handle vote results tables from different years)
    column_renaming_map = {
        "Polling Station Number/Numéro du bureau de scrutin": "Poll",
        "Polling Station Name/Nom du bureau de scrutin": "PollStationName",
        "Merge With/Fusionné avec": "MergedWith",
        "Candidate’s Family Name/Nom de famille du candidat":
            "CandidateLastName",
        "Candidate’s First Name/Prénom du candidat": "CandidateFirstName",
        "Candidate’s Middle Name/Second prénom du candidat":
            "CandidateMiddleName",
        "Candidate's Family Name/Nom de famille du candidat":
            "CandidateLastName",
        "Candidate's First Name/Prénom du candidat": "CandidateFirstName",
        "Candidate's Middle Name/Second prénom du candidat":
            "CandidateMiddleName",
        "Political Affiliation Name_English/Appartenance politique_Anglais":
            "Party",
        "Candidate Poll Votes Count/Votes du candidat pour le bureau":
            "Votes",
        "Electors for Polling Station/Électeurs du bureau": "Electors",
        "Rejected Ballots for Polling Station/Bulletins rejetés du bureau":
            "RejectedBallots",
        "Incumbent Indicator/Indicateur_Candidat sortant":
            "IncumbentIndicator",
        "Elected Candidate Indicator/Indicateur du candidat élu":
            "ElectedIndicator",
        "Electoral District Name_English/Nom de circonscription_Anglais":
            "DistrictName",
        "Electoral District Number/Numéro de circonscription":
            "DistrictNumber",
        "Void Poll Indicator/Indicateur de bureau supprimé":
            "VoidIndicator",
        "No Poll Held Indicator/Indicateur de bureau sans scrutin":
            "NoPollIndicator"
    }

    # text encoding changes in 2015 (oh boy)
    csv_encoding = votes_encodings.get(year, "utf-8")
    # regex pattern for riding file
    pat = re.compile(r".*pollresults.*([0-9]{5}).*")

    with ZipFile(votesfile, "r") as zf:
        for fname in zf.namelist():
            # iterate over CSV files in the zip and extract
            # riding names and numbers from first line
            match = pat.match(fname)
            if match is not None:
                # if ridings is None, get all ridings, else matchers
                if ridings is None or match.group(1) in riding_nos:
                    temp_df = pd.read_csv(zf.open(fname), encoding=csv_encoding,
                                          dtype=dtype_map)
                    df = pd.concat((df, temp_df), ignore_index=True)

    # drop redundant French columns
    df = df.drop(french_columns, axis=1)

    # apply some sanity-preserving column renaming
    df = df.rename(columns=column_renaming_map)

    # for some reason, DistrictName ends with " in 2008
    df["DistrictName"] = df["DistrictName"].str.strip("\"")

    # distinguish value in Party column where multiple Independent candidates
    # appear in same riding (N.B. sometimes it's called "No Affiliation")
    df.loc[df["Party"] == "No Affiliation", "Party"] = "Independent"
    df_indep_cands = (df[df["Party"] == "Independent"]
                      .get(["DistrictNumber", "CandidateFirstName",
                            "CandidateLastName"])
                      .drop_duplicates())
    cand_rename_map = {}
    for district_number, grp in df_indep_cands.groupby("DistrictNumber"):
        ind_counter = 0
        grp_unique = grp[["CandidateFirstName",
                          "CandidateLastName"]].drop_duplicates()
        if len(grp_unique) > 1:
            for irow, row in grp_unique.iterrows():
                ind_counter += 1
                cand_rename_map[
                    (row["CandidateFirstName"],
                     row["CandidateLastName"])
                ] = f"Independent-{ind_counter:02d}"
    for cand_names, party_str in cand_rename_map.items():
        df.loc[(df["CandidateFirstName"] == cand_names[0])
               & (df["CandidateLastName"] == cand_names[1]),
               "Party"] = party_str

    # rename "People's Party" to "People's Party - PPC" for consistency over
    # multiple elections
    df.loc[df["Party"] == "People's Party", "Party"] = "People's Party - PPC"

    # create a column with the numeric part of the poll number for merging
    # with the GeoDataFrames (exclude entirely non-numeric "Special Rules"
    # polls, i.e. vote by mail etc.)
    df["PD_NUM"] = df["Poll"].map(lambda val: (get_int_part(val)
                                               if not "S/R" in val else 0))

    return df


def load_vote_data(ridings=None, area=None, year=2021):
    """
    Load dataframe with vote results from list of ridings (possibly
    spanning multiple provinces)

    Parameters
    ----------
    ridings : list
        riding names
    area : str
        name of predefined area
    year : int
        year for which to load data

    Returns
    -------
    pd.DataFrame
    """
    if area is not None:
        ridings = validate_ridings(areas.get(area, []), year)
    elif ridings is not None:
        ridings = validate_ridings(ridings, year)

    riding_codes = apply_riding_map(ridings=ridings, year=year)
    codes = list(set([int(str(rid)[:2]) for rid in riding_codes]))

    df = pd.DataFrame()

    for province_code in codes:
        province = codeprovs[province_code]
        temp_df = load_vote_data_prov(year=year, province=province,
                                      ridings=ridings)
        df = pd.concat((df, temp_df), ignore_index=True)

    return df


def split_vote_data(df_vote):
    """
    Split vote data into election-day, advance and "special" parts based
    on polling division number

    Parameters
    ----------
    df_vote : pd.DataFrame

    Returns
    -------
    dict
        with election-day, advance and special dataframes
    """
    df_eday = df_vote[(df_vote["PD_NUM"] > 0)
                      & (df_vote["PD_NUM"] < 600)].copy()
    df_adv = df_vote[df_vote["PD_NUM"] >= 600].copy()
    df_special = df_vote.loc[df_vote["Poll"].str.match(r"^ S")].copy()

    return {
        "eday": df_eday,
        "advance": df_adv,
        "special": df_special
    }


def make_candidate_map(df_vote):
    """
    Make a map from riding number to party to candidate name.

    Parameters
    ----------
    df_vote : pd.DataFrame

    Returns
    -------
    dict
    """
    candidate_map = {}
    candidate_df = (df_vote[["DistrictNumber", "Party",
                             "CandidateFirstName", "CandidateMiddleName",
                             "CandidateLastName"]]
                    .drop_duplicates()
                    .fillna(""))
    for fed_num, grp in candidate_df.groupby("DistrictNumber"):
        candidate_map[fed_num] = {}
        for party, candidate_row in grp.set_index("Party").iterrows():
            candidate_map[fed_num][party] = (
                f"{candidate_row['CandidateLastName']}, "
                + f"{candidate_row['CandidateFirstName']}"
            )
            if len(candidate_row["CandidateMiddleName"]) > 0:
                candidate_map[fed_num][party] += (
                    f" {candidate_row['CandidateMiddleName']}"
                )

    return candidate_map


def merge_eday_polls(merge_map, df_eday):
    """
    Merge election-day polls whose vote-counts are merged (due to
    insufficient number of votes at a poll for anonymity purposes)

    Parameters
    ----------
    merge_map : dict
        mapping district numbers to poll numbers to the merge-sets they
        belong to (usually a singleton set)
    df_eday : pd.DataFrame
        containing polls and votes data

    Returns
    -------
    df_eday_merged
        with polls merged based on the MergedWith column
    """
    # sort data to make sure the PD_NUM gets assigned the same as in geometry
    df_eday_merged = (df_eday
                      .sort_values(["DistrictNumber", "PD_NUM", "Poll"])
                      .copy())

    df_eday_merged["MergeSet"] = (
        df_eday_merged
        .apply(lambda row: merge_map[row["DistrictNumber"]][row["PD_NUM"]],
               axis=1)
    )

    # merge rows belonging to same merge-sets
    def merge_grpfun(grp):
        if len(grp) == 1:
            return grp.iloc[0]
        grp = grp.sort_values(["PD_NUM", "Poll"])
        retsrs = grp.iloc[0].copy()
        for col in ["Votes", "Electors",
                    "RejectedBallots"]:
            retsrs[col] = grp[col].sum()
        if "Poll" in grp.columns:
            retsrs["Poll"] = ", ".join(grp["Poll"].str.strip())
        return retsrs

    # save column order to put it back the way it was after the merge
    cols = df_eday_merged.columns

    df_eday_merged = (
        df_eday_merged
        .groupby(["Party", "MergeSet"])
        .apply(merge_grpfun, include_groups=False)
        .reset_index()
        .sort_values(["DistrictNumber", "PD_NUM", "Party"])
        .reindex(cols, axis=1)
    )

    return df_eday_merged


def pivot_vote_tables(df_vote, values_column="Votes"):
    """
    Divite votes table into tables for each district and pivot them
    so that votes for each party form columns and each polling division
    a single row (instead of one row per party).
    TODO: allow election-day + advance votes to be the values_column (pivot twice and sum dataframes)

    Parameters
    ----------
    df_vote : pd.DataFrame
    values_column : str
        name of column to use for values in party columns

    Returns
    -------
    dict
        mapping district number to pivoted vote table
    """
    df_pivots = {}
    for fed_num, grp in df_vote.groupby("DistrictNumber"):
        df_pivots[fed_num] = (
            grp[["DistrictName", "Poll", "PD_NUM",
                 "Party", values_column]]
            .pivot(index=["DistrictName", "Poll", "PD_NUM"],
                   columns="Party", values=values_column)
            .reset_index()
            .sort_values("PD_NUM")
        )
        df_pivots[fed_num][f"Total{values_column}"] = (df_pivots[fed_num]
                                                       .iloc[:, 3:-1]
                                                       .sum(axis=1))

    return df_pivots