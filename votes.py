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

    # create a column with the numeric part of the poll number to merge with the geodataframes
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