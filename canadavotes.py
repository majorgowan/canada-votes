"""
-------------------------------------------------------
main program for canada votes program
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
import pandas as pd
import geopandas as gpd
from .utils import validate_ridings
from .constants import areas
from . import votes, geometry, viz


class CanadaVotes:
    def __init__(self, years=2021, area=None, ridings=None):
        # initialize data to empty dictionary
        self.years = []
        self.data = {}
        self.ridings = set()
        self.loaded = {}
        self.add_ridings(area=area, ridings=ridings)

        if isinstance(years, int):
            self.add_year(years)
        elif isinstance(years, list):
            for year in years:
                self.add_year(year)

    def add_year(self, year):
        if year not in [2008, 2011, 2015, 2019, 2021]:
            print("year {year} invalid")
            print("year must be one of: 2008, 2011, 2015, 2019, 2021")
        if year not in self.years:
            self.years = sorted([year] + self.years)
            self._init_year(year)
        return self

    def add_ridings(self, area=None, ridings=None):
        if ridings is not None:
            self.ridings = self.ridings.union(ridings)
        if area is not None:
            self.ridings = self.ridings.union(areas.get(area, []))
        return self

    def _init_year(self, year):
        # initialize empty dataframes for new year
        self.data[year] = {
            "gdf_eday": gpd.GeoDataFrame(),
            "gdf_eday_merged": gpd.GeoDataFrame(),
            "gdf_advance": gpd.GeoDataFrame(),
            "gdf_ridings": gpd.GeoDataFrame(),
            "vdf": pd.DataFrame()
        }
        self.loaded[year] = set()

    @staticmethod
    def _load_geometries(year, ridings, robust=False):
        gdf_eday = geometry.load_geometries(ridings=ridings, year=year,
                                            advance=False)
        gdf_advance = geometry.load_geometries(ridings=ridings,
                                               year=year,
                                               advance=True)
        gdf_ridings = geometry.dissolve_ridings(gdf=gdf_advance, robust=robust)

        return gdf_eday, gdf_advance, gdf_ridings

    @staticmethod
    def _load_votes(year, ridings):
        return votes.load_vote_data(ridings=ridings, year=year)

    @staticmethod
    def _merge_votes(gdf_eday, gdf_advance, vdf, robust=False):
        # election-day polls
        gdf_eday = geometry.merge_votes(gdf=gdf_eday, df_vote=vdf)
        gdf_eday_merged = (geometry
                           .combine_mergedwith_columns(gdf=gdf_eday,
                                                       robust=robust))
        # advance polls
        gdf_advance = (geometry
                       .merge_votes(gdf=gdf_advance,
                                    df_vote=vdf))

        # add columns for election-day votes in advance poll areas
        gdf_advance = (
            votes.add_eday_votes(gdf_eday=gdf_eday,
                                 gdf_advance=gdf_advance)
        )

        # set index on gdf_eday for consistency
        gdf_eday = gdf_eday.set_index(["DistrictName", "Party", "PD_NUM"])

        return gdf_eday, gdf_eday_merged, gdf_advance

    def _load_all(self, year, ridings, robust=False):
        (gdf_eday,
         gdf_advance,
         gdf_ridings) = self._load_geometries(year=year,
                                              ridings=ridings,
                                              robust=robust)
        vdf = self._load_votes(year=year, ridings=ridings)
        (gdf_eday,
         gdf_eday_merged,
         gdf_advance) = self._merge_votes(gdf_eday=gdf_eday,
                                          gdf_advance=gdf_advance,
                                          vdf=vdf, robust=robust)
        # append new data to object data
        self.data[year]["gdf_eday"] = pd.concat(
            (self.data[year]["gdf_eday"], gdf_eday)
        )
        self.data[year]["gdf_eday_merged"] = pd.concat(
            (self.data[year]["gdf_eday_merged"], gdf_eday_merged)
        )
        self.data[year]["gdf_advance"] = pd.concat(
            (self.data[year]["gdf_advance"], gdf_advance)
        )
        self.data[year]["gdf_ridings"] = pd.concat(
            (self.data[year]["gdf_ridings"], gdf_ridings)
        )
        self.data[year]["vdf"] = pd.concat(
            (self.data[year]["vdf"], vdf)
        )

        # update loaded dictionary
        self.loaded[year] = self.loaded[year].union(ridings)

    def load(self, robust=True):
        """
        load and merge all data for ridings specified
        """
        for year in self.years:
            print(f"Loading year {year} . . . ", end="")
            new_ridings = validate_ridings(
                list(self.ridings.difference(self.loaded[year])),
                year=year
            )
            if len(list(new_ridings)) > 0:
                self._load_all(year, new_ridings, robust=robust)
            print("loaded.")

        return self

    def plot_votes(self, party, year=None, plot_variable="VoteFraction",
                   figsize=None, ridings_args=None, basemap=None,
                   advance=False, filename=None, **kwargs):
        if len(self.data) == 0:
            print("please load some data first")
            return None

        if year is None:
            year = list(self.data.keys())[0]

        gdf_ridings = self.data[year]["gdf_ridings"]
        if advance:
            gdf_plot = self.data[year]["gdf_advance"]
        else:
            gdf_plot = self.data[year]["gdf_eday_merged"]

        viz.votes_plot(gdf_plot, party=party, gdf_ridings=gdf_ridings,
                       plot_variable=plot_variable, figsize=figsize,
                       ridings_args=ridings_args, basemap=basemap,
                       year=year, **kwargs)
        if filename is not None:
            viz.savepng(filename)

    def plot_compare(self, party1, party2, year=None,
                     plot_variable="VoteFraction",
                     figsize=None, ridings_args=None, basemap=None,
                     advance=False, filename=None, **kwargs):
        if len(self.data) == 0:
            print("please load some data first")
            return None

        if year is None:
            year = list(self.data.keys())[0]

        gdf_ridings = self.data[year]["gdf_ridings"]
        if advance:
            gdf_plot = self.data[year]["gdf_advance"]
        else:
            gdf_plot = self.data[year]["gdf_eday_merged"]

        viz.votes_comparison_plot(gdf_plot, party1=party1, party2=party2,
                                  gdf_ridings=gdf_ridings,
                                  plot_variable=plot_variable,
                                  figsize=figsize, ridings_args=ridings_args,
                                  basemap=basemap, year=year, **kwargs)
        if filename is not None:
            viz.savepng(filename)

    def parties(self, year):
        """
        Returns
        -------
        list
            parties with candidates in the selected ridings
        """
        if len(self.data[year]["vdf"]) > 0:
            return sorted(self.data[year]["vdf"]["Party"].unique().tolist())
        else:
            return []

    def votes(self, year, by="Party", key="Votes"):
        """
        Parameters
        ----------
        year : int
            election year
        by : str
            either "party" or "candidate"
        key : str
            either "Votes" or "Fraction"

        Returns
        -------
        pd.DataFrame
            vote totals
        """
        if "vdf" in self.data[year]:
            if by.lower() == "party":
                df = (self.data[year]["vdf"]
                      .groupby("Party")
                      .aggregate({"Votes": "sum", "TotalVotes": "sum"}))
                df["VoteFraction"] = df["Votes"].divide(df["TotalVotes"])
                if key.lower() == "fraction":
                    return df.sort_values("VoteFraction", ascending=False)
                else:
                    return df.sort_values("Votes", ascending=False)

            elif by.lower() == "candidate":
                df = (self.data[year]["vdf"]
                      .get(["Party", "DistrictName",
                            "CandidateLastName", "CandidateFirstName",
                            "ElectedIndicator", "Votes", "TotalVotes"])
                      .copy())
                df["Estring"] = (df["ElectedIndicator"]
                                 .map(lambda val: ("  (Elected)"
                                                   if val == "Y" else "")))
                df["Candidate"] = (df["CandidateLastName"]
                                   + ", " + df["CandidateFirstName"]
                                   + df["Estring"])
                df = (df
                      .groupby(["Candidate", "Party", "DistrictName"])
                      .aggregate({"Votes": "sum", "TotalVotes": "sum"}))
                df["VoteFraction"] = df["Votes"].divide(df["TotalVotes"])
                if key.lower() == "fraction":
                    return df.sort_values("VoteFraction", ascending=False)
                else:
                    return df.sort_values("Votes", ascending=False)
            else:
                print("parameter 'by' must be 'Party' or 'Candidate'")
        else:
            print("please load votes data with load() or load_votes()")
        return None

    def __repr__(self):
        return_str = f"CanadaVotes object\n"
        return_str += f"Years:"
        for year in self.years:
            return_str += f" {year}"
        return_str += "\n"
        return_str += f"Ridings:\n"
        for rid in self.ridings:
            return_str += f"\t{rid}\n"
        for year in self.data:
            return_str += f"Election {year} parties:\n"
            parties = self.parties(year)
            if len(list(parties)) > 0:
                for party in parties:
                    return_str += f"\t{party}\n"
            else:
                return_str += "\tnot loaded\n"
        return_str += "\n"
        return return_str
