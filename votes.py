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
from .constants import datadir, provcodes, codeprovs, votes_encodings
from .utils import (get_int_part, area_to_ridings, apply_riding_map,
                    validate_ridings)


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

    # create column with the total number of votes for all parties at that poll
    df_totvotes = (df
                   .get(["DistrictName", "Poll", "Votes"])
                   .groupby(["DistrictName", "Poll"], as_index=False)
                   .sum()
                   .rename(columns={"Votes": "TotalVotes"}))
    df = df.merge(df_totvotes, on=["DistrictName", "Poll"], how="left")

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
    df["PD_NUM"] = (df.loc[~df["Poll"].str.contains("S/R"), "Poll"]
                    .map(get_int_part).astype("int"))

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
        ridings = area_to_ridings(area, year)
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


def compute_vote_fraction(df_vote):
    """
    Calculate fraction of votes earned by each candidate

    Parameters
    ----------
    df_vote : pd.DataFrame
        containing vote data

    Returns
    -------
    pd.DataFrame or gpd.GeoDataFrame
    """
    df_vote = df_vote.copy()

    # Compute fraction of all (potential) electors and fraction of all voters
    df_vote["PotentialVoteFraction"] = (df_vote["Votes"]
                                        .divide(df_vote["Electors"]))
    df_vote["VoteFraction"] = (df_vote["Votes"]
                               .divide(df_vote["TotalVotes"]))
    # replace any nans with zero (probably total votes were zero)
    df_vote["VoteFraction"] = df_vote["VoteFraction"].fillna(0.0)
    df_vote["PotentialVoteFraction"] = (df_vote["PotentialVoteFraction"]
                                        .fillna(0.0))
    return df_vote


def add_eday_votes(gdf_eday, gdf_advance):
    """
    add election-day votes to the associated advance poll rows

    Parameters
    ----------
    gdf_eday : gpd.GeoDataFrame
        with election-day polling station boundaries and votes
    gdf_advance : gpd.GeoDataFrame
        with advance-poll station boundaries and votes

    Returns
    -------
    gdf_advance
        with new column for election day votes
    """
    gdf_eday_votes = (gdf_eday
                      .get(["DistrictName", "Party",
                            "ADV_POLL_N", "Votes", "TotalVotes"])
                      .groupby(["DistrictName", "Party",
                                "ADV_POLL_N"],
                               as_index=False)
                      .sum()
                      .rename(columns={"ADV_POLL_N": "PD_NUM",
                                       "Votes": "ElectionDayVotes",
                                       "TotalVotes": "TotalElectionDayVotes"}))
    gdf_advance = (gdf_advance
                   .merge(gdf_eday_votes,
                          on=["DistrictName", "Party", "PD_NUM"],
                          how="left"))

    # compute total vote fraction
    gdf_advance["AllVoteFraction"] = (
        (gdf_advance["Votes"] + gdf_advance["ElectionDayVotes"])
        .divide((gdf_advance["TotalVotes"]
                 + gdf_advance["TotalElectionDayVotes"]))
    )

    # compute advance vote fraction (if not already computed)
    if "VoteFraction" not in gdf_advance.columns:
        gdf_advance["VoteFraction"] = (gdf_advance["Votes"]
                                       .divide(gdf_advance["TotalVotes"]))

    gdf_advance = gdf_advance.set_index(["DistrictName",
                                         "Party",
                                         "PD_NUM"])

    return gdf_advance
