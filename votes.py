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
from .constants import datadir, provcodes, codeprovs
from .utils import get_int_part, apply_riding_map


# TODO: allow handling parties with no votes in a poll to not break everything

def load_vote_data_prov(province):
    """
    Load dataframe with vote results from single province

    Parameters
    ----------
    province : str
        two character province abbreviation

    Returns
    -------
    pd.DataFrame
    """
    provcode = provcodes[province]
    votesfile = os.path.join(datadir,
                             f"pollresults_resultatsbureau{provcode}.zip")

    df = pd.DataFrame()

    french_columns = [
        "Electoral District Name_French/Nom de circonscription_Français",
        "Political Affiliation Name_French/Appartenance politique_Français"
    ]
    dtype_map = {
        "Merge With/Fusionné avec": "str",
        "Polling Station Number/Numéro du bureau de scrutin": "str"
    }
    column_renaming_map = {
        "Polling Station Number/Numéro du bureau de scrutin": "Poll",
        "Polling Station Name/Nom du bureau de scrutin": "PollStationName",
        "Merge With/Fusionné avec": "MergedWith",
        "Candidate’s Family Name/Nom de famille du candidat":
            "CandidateLastName",
        "Candidate’s First Name/Prénom du candidat": "CandidateFirstName",
        "Candidate’s Middle Name/Second prénom du candidat":
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

    with ZipFile(votesfile, "r") as zf:
        for fname in zf.namelist():
            # iterate over CSV files in the zip and extract
            # riding names and numbers from first line
            if re.match(r"pollresults.*csv", fname):
                temp_df = pd.read_csv(zf.open(fname), dtype=dtype_map)
                df = pd.concat((df, temp_df), ignore_index=True)

    # drop redundant French columns
    df = df.drop(french_columns, axis=1)

    # apply some sanity-preserving column renaming
    df = df.rename(columns=column_renaming_map)

    # drop rows not associated with a polling station ("Special Voting Rules")
    df = df[~df["Poll"].str.contains("S/R")]

    # create column with the total number of votes for all parties at that poll
    df_totvotes = (df
                   .get(["DistrictName", "Poll", "Votes"])
                   .groupby(["DistrictName", "Poll"], as_index=False)
                   .sum()
                   .rename(columns={"Votes": "TotalVotes"}))
    df = df.merge(df_totvotes, on=["DistrictName", "Poll"], how="left")

    # create a column with the numeric part of the poll number for merging
    # with the GeoDataFrames
    df["PD_NUM"] = df["Poll"].map(get_int_part).astype("int")

    return df


def load_vote_data(ridings=None, area=None):
    """

    Parameters
    ----------
    ridings : list
        riding names
    area : str
        name of predefined area

    Returns
    -------
    pd.DataFrame
    """
    riding_codes = apply_riding_map(ridings=ridings, area=area)
    pcodes = list(set([int(str(rid)[:2]) for rid in riding_codes]))

    df = pd.DataFrame()

    for provcode in pcodes:
        province = codeprovs[provcode]
        temp_df = load_vote_data_prov(province)
        # keep only ridings
        temp_df = temp_df[temp_df["DistrictNumber"].isin(riding_codes)]
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

    gdf_advance = gdf_advance.set_index(["DistrictName",
                                         "Party",
                                         "PD_NUM"])

    return gdf_advance