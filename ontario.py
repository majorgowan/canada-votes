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
from .geometry import robust_dissolve, dissolve_ridings


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

    # drop By Election rows
    df_interest = df_interest.loc[~df_interest["EventNameEnglish"]
                                  .str.contains(r"[bB]y.[eE]lection")]
    df_candidates = df_candidates.loc[~df_candidates["EventNameEnglish"]
                                      .str.contains(r"[bB]y.[eE]lection")]
    df_votes = df_votes.loc[~df_votes["EventNameEnglish"]
                            .str.contains(r"[bB]y.[eE]lection")]

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
                         "ElectoralDistrictNumber": "DistrictNumber",
                         "NameOfCandidates": "Candidate",
                         "PoliticalInterestCode": "PartyCode"})
    )
    df_candidates["Candidate"] = df_candidates["Candidate"].str.upper()

    df_votes = (
        df_votes
        .drop([col for col in df_votes.columns
               if "French" in col], axis=1)
        .rename(columns={"EventNameEnglish": "EventName",
                         "ElectoralDistrictNameEnglish": "DistrictName",
                         "AcceptedBallotCount": "Votes",
                         "NameOfCandidates": "Candidate"})
    )
    # make candidate name conform to "Given Names Last Name"
    # like in df_candidates (good grief!)
    def name_switch(s):
        split = s.upper().split(",")
        if len(split) == 2:
            return (split[1].strip() + " " + split[0].strip()).upper()
        else:
            return s.upper()
    df_votes["Candidate"] = df_votes["Candidate"].map(name_switch)

    # extract district number from districtname in votes file
    df_votes["DistrictNumber"] = (df_votes["DistrictName"]
                                  .str.slice(0,3)
                                  .astype(int))

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

    # merge party name into votes
    df_votes = df_votes.merge(df_candidates[["Candidate", "PartyCode",
                                             "Party"]],
                              on="Candidate", how="left")

    return {
        "candidates": df_candidates,
        "votes": df_votes
    }


def make_ontario_riding_map(df_votes, inverse=False):
    if inverse:
        return {row["DistrictName"]: row["DistrictNumber"]
                for dn, row
                in (df_votes[["DistrictNumber", "DistrictName"]]
                    .drop_duplicates()
                    .iterrows())}
    else:
        return {row["DistrictNumber"]: row["DistrictName"]
                for dn, row
                in (df_votes[["DistrictNumber", "DistrictName"]]
                    .drop_duplicates()
                    .iterrows())}


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

    # check for subfolder inside zip file
    with ZipFile(zipname) as zf:
        if "/" in zf.namelist()[0]:
            folder_name = zf.namelist()[0].split("/")[0]
        else:
            folder_name = None

    # now read shapefile
    if folder_name is not None:
        gdf = gpd.read_file(f"{zipname}!{folder_name}",
                            encoding="latin-1")
    else:
        gdf = gpd.read_file(zipname)
        # force some dtypes
        gdf["PD_NUMBER"] = gdf["PD_NUMBER"].astype(int)
        gdf["ED_ID"] = gdf["ED_ID"].astype(int)

    gdf = gdf.to_crs(epsg=4326)

    # drop French columns
    gdf = (
        gdf
        .drop([col for col in gdf.columns
               if "_FR" in col], axis=1)
        .rename(columns={"ED_NAME_EN": "DistrictName",
                         "ED_ID": "DistrictNumber",
                         "PD_NUMBER": "PD_NUM"})
    )
    gdf["PD_NUM"] = gdf["PD_NUM"].astype(int)

    # replace em-dashes bzw. \x97 with double dashes
    gdf["DistrictName"] = (gdf["DistrictName"]
                           .map(lambda s: s.replace("—", "--")))
    gdf["DistrictName"] = (gdf["DistrictName"]
                           .map(lambda s: s.replace("\x97", "--")))

    # filter by riding list
    if ridings is not None:
        gdf = gdf[gdf["DistrictName"].isin(ridings)]

    return gdf


def merge_combined_with(df_votes, gdf):
    """
    Merge rows in votes DataFrame (sum votes etc. and combine pollnumbers)
    and dissolve geometries in GeoDataFrame based on CombinedWith column
    in votes dataframe.

    Parameters
    ----------
    df_votes : pd.DataFrame
    gdf : gpd.GeoDataFrame

    Returns
    -------
    pd.DataFrame, gpd.GeoDataFrame
    """
    # add combined-with column to
    gdf = gdf.merge((df_votes[["DistrictName", "PD_NUM", "CombinedWith"]]
                     .drop_duplicates()),
                    on=["DistrictName", "PD_NUM"], how="left")
    gdf_combined = gdf[~gdf["CombinedWith"].isna()]
    gdf = gdf.drop(gdf_combined.index)
    # drop any rows with non-integer CombinedWith values
    gdf_combined = gdf_combined[~(gdf_combined["CombinedWith"]
                                  .str.contains("ADV"))]
    gdf_combined["PD_NUM"] = (gdf_combined["CombinedWith"]
                              .map(lambda s: get_int_part(s)))
    gdf_combined = robust_dissolve(
        gdf_combined, by=["DistrictName", "PD_NUM"],
        aggfunc={c: (lambda col: col.iloc[0])
                 for c in gdf_combined.columns
                 if c not in ["PD_NUM", "DistrictName",
                              "geometry"]}
    ).reset_index()

    gdf = (pd.concat((gdf, gdf_combined), ignore_index=True)
           .sort_values(["DistrictNumber", "PD_NUM"]))
    gdf.index = range(len(gdf))

    # grouping function for aggregating votes
    def grpfun(grp):
        # construct composit pollnumber starting with the CombinedWith value
        target = grp.name[1]
        pollnumber = (f"{target}, "
                      + ", ".join([pn for pn in grp["PollNumber"].unique()
                                   if pn != target]))
        # use first row for general columns
        return_row = grp.sort_values("PD_NUM", ascending=False).iloc[0].copy()
        return_row["PollNumber"] = pollnumber
        # sum these columns
        for name in ["BallotsFromBoxesRejectedAsMarkings",
                     "BallotsFromBoxesUnmarkedByVoters",
                     "BallotsDeclinedByVoters",
                     "NamesOnListOfElectors",
                     "Votes"]:
            return_row[name] = grp[name].sum()
        return return_row

    # remove rows involved in combinations
    df_combined = df_votes[~df_votes["CombinedWith"].isna()]
    df_votes = df_votes.drop(df_combined.index)
    df_combined = (df_combined
                   .groupby(["DistrictName", "CombinedWith", "Party"])
                   .apply(grpfun, include_groups=False)
                   .reset_index())
    df_combined = df_combined[df_votes.columns]

    df_votes = (pd.concat((df_votes, df_combined),
                          ignore_index=True)
                .sort_values(["DistrictNumber", "PollNumber", "Party"]))
    df_votes.index = range(len(df_votes))

    return df_votes, gdf


def pivot_and_merge_geometries(df_votes, gdf, normalize=False):
    """
    Create pivot tables with vote totals for each party in each riding
    and merge in the geometries

    Parameters
    ----------
    df_votes : pd.DataFrame
    gdf : gpd.DataFrame
    normalize : bool

    Returns
    -------
    dict
        mapping district numbers to pivot tables with votes and geometries
    """
    pivots_dict = {}
    for dnum in df_votes["DistrictNumber"].unique():
        df_pivot = (df_votes[(df_votes["DistrictNumber"] == dnum)
                         & (~df_votes["PollNumber"].str.contains("ADV"))]
                    .pivot(values="Votes",
                           index=["DistrictNumber", "DistrictName",
                                  "PD_NUM", "PollNumber"],
                           columns="Party"))
        df_pivot["TotalVotes"] = df_pivot.sum(axis=1)
        if normalize:
            df_pivot = df_pivot.divide(df_pivot["TotalVotes"], axis=0)
        df_pivot = df_pivot.reset_index()
        # merge geometries
        df_pivot = gpd.GeoDataFrame(
            df_pivot.merge(gdf[["DistrictNumber","PD_NUM", "geometry"]],
                           on=["DistrictNumber", "PD_NUM"], how="left")
        )
        pivots_dict[dnum] = df_pivot

    return pivots_dict


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


class OntarioVotes:
    def __init__(self, years=2022, ridings=None):
        # initialize data to empty dictionary
        self.years = []
        self.data = {}
        self.ridings = set()
        self.loaded = {}
        self.add_ridings(ridings=ridings)

        if isinstance(years, int):
            self.add_year(years)
        elif isinstance(years, list):
            for year in years:
                self.add_year(year)

    def add_year(self, year):
        if year not in [2018, 2022]:
            print("year {year} invalid")
            print("year must be one of: 2018, 2022")
        if year not in self.years:
            self.years = sorted([year] + self.years)
            self._init_year(year)
        return self

    def add_ridings(self, ridings=None):
        if ridings is not None:
            if isinstance(ridings, str):
                ridings = [ridings]
            self.ridings = self.ridings.union(ridings)
        return self

    def _init_year(self, year):
        # initialize empty dicts for new year
        self.data[year] = {
            "gdf": {},
            "vdf": {},
            "candidate_map": {}
        }
        self.loaded[year] = set()

    @staticmethod
    def _load_geometries(year, ridings, robust=False):
        gdf = load_ontario_geometries(ridings=ridings, year=year)
        gdf_ridings = dissolve_ridings(gdf=gdf,
                                       district_column="DistrictNumber",
                                       robust=robust)
        return {
            "stations": gdf,
            "ridings": gdf_ridings
        }

    @staticmethod
    def _load_votes(year, ridings):
        # load votes for selected year and ridings list
        return load_ontario_vote_data(ridings=ridings, year=year)

    def _load_all(self, year, ridings):
        # load raw geometries and votes
        gdf_dict = self._load_geometries(year=year, ridings=ridings,
                                         robust=True)
        vdf_dict = self._load_votes(year=year, ridings=ridings)

        # build candidate map
        candidate_map = make_candidate_map(vdf_dict["candidates"])

        # merge map from election-day votes table
        (vdf_dict["votes"],
         gdf_dict["stations"]) = merge_combined_with(vdf_dict["votes"],
                                                     gdf_dict["stations"])

        self.data[year]["vdf"] = vdf_dict
        self.data[year]["gdf"] = gdf_dict
        self.data[year]["candidate_map"] = candidate_map

    def load(self, robust=True):
        """
        load and merge all data for ridings specified
        """
        for year in self.years:
            print(f"Loading year {year} . . . ", end="")
            self._load_all(year, self.ridings)
            print("loaded.")

        return self

    def __getitem__(self, item):
        return self.data[item]

    def __repr__(self):
        return_str = f"OntarioVotes object\n"
        return_str += f"Years:"
        for year in self.years:
            return_str += f" {year}"
        return_str += "\n"
        return_str += f"Ridings:\n"
        if self.ridings is not None:
            for rid in self.ridings:
                return_str += f"\t{rid}\n"
            return_str += "\n"
        return return_str
