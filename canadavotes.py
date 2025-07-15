"""
-------------------------------------------------------
main program for canada votes program
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
import pandas as pd
from .constants import areas
from . import votes, geometry, utils, viz


class CanadaVotes:
    def __init__(self, years=2021, area=None, ridings=None):
        # initialize data to empty dictionary
        self.years = []
        self.data = {}
        self.ridings = set()
        self.loaded = {}
        self.add_ridings(ridings=ridings, area=area)

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

    def add_ridings(self, ridings=None, area=None):
        if ridings is not None:
            if isinstance(ridings, str):
                ridings = [ridings]
            self.ridings = self.ridings.union(ridings)
        if area is not None:
            if area.lower() not in areas:
                print(f"Area '{area}' not defined. Please select one of:")
                for area in areas:
                    print(f"{area}", end="  ")
            else:
                self.ridings = self.ridings.union(areas.get(area.lower()))
        return self

    def drop_ridings(self, ridings):
        if isinstance(ridings, str):
            ridings = [ridings]
        for year in self.years:
            # remove the requested ridings from each data table
            valid_ridings = utils.validate_ridings(ridings)
            if len(list(valid_ridings)) == 0:
                continue

            # remove data from all the tables
            for vdf_key in self.data[year]["vdf"]:
                self.data[year]["vdf"][vdf_key] = (
                    self.data[year]["vdf"][vdf_key]
                    .get(~self.data[year]["vdf"][vdf_key]["DistrictName"]
                         .isin(valid_ridings))
                )
            fed_nums = utils.apply_riding_map(year, valid_ridings)
            for gdf_key in self.data[year]["gdf"]:
                self.data[year]["gdf"][gdf_key] = (
                    self.data[year]["gdf"][gdf_key]
                    .get(~self.data[year]["gdf"][gdf_key]["FED_NUM"]
                         .isin(fed_nums))
                )
            # remove candidates from candidates map
            self.data[year]["candidate_map"] = {
                k: v for k, v in self.data[year]["candidate_map"].items()
                if k not in fed_nums
            }

            self.loaded[year].difference_update(valid_ridings)

        # remove the requested ridings from the object
        self.ridings.difference_update(ridings)
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
        gdf_eday = geometry.load_geometries(ridings=ridings, year=year,
                                            advance=False)
        gdf_advance = geometry.load_geometries(ridings=ridings,
                                               year=year,
                                               advance=True)
        gdf_ridings = geometry.dissolve_ridings(gdf=gdf_advance, robust=robust)

        return {
            "eday": gdf_eday,
            "advance": gdf_advance,
            "ridings": gdf_ridings
        }

    @staticmethod
    def _load_votes(year, ridings):
        # load votes for selected year and ridings list
        vdf = votes.load_vote_data(ridings=ridings, year=year)
        # split votes into election-day, advance and special
        return votes.split_vote_data(vdf)

    def _load_all(self, year, ridings):
        # load raw geometries and votes
        gdf_dict = self._load_geometries(year=year, ridings=ridings)
        vdf_dict = self._load_votes(year=year, ridings=ridings)

        # add election-day votes to advance-votes table
        vdf_dict["advance"] = utils.add_eday_votes(vdf_dict["eday"],
                                                   vdf_dict["advance"],
                                                   gdf_dict["eday"])

        # build candidate map
        candidate_map = votes.make_candidate_map(vdf_dict["eday"])

        # build merge map from election-day votes table
        merge_sets_dict = utils.find_merge_sets(vdf_dict["eday"])
        merge_map = utils.make_merge_map(vdf_dict["eday"], merge_sets_dict)

        # apply merge-map to votes
        vdf_dict["eday_merged"] = votes.merge_eday_polls(merge_map,
                                                         vdf_dict["eday"])
        gdf_dict["eday_merged"] = geometry.dissolve_mergedwith(merge_map,
                                                               gdf_dict["eday"])

        for gdf_key in ("eday", "eday_merged", "advance", "ridings"):
            if gdf_key in self.data[year]["gdf"]:
                self.data[year]["gdf"][gdf_key] = pd.concat(
                    (self.data[year]["gdf"][gdf_key],
                     gdf_dict[gdf_key]),
                    ignore_index=True
                )
            else:
                self.data[year]["gdf"][gdf_key] = gdf_dict[gdf_key]

        for vdf_key in ("eday", "eday_merged", "advance", "special"):
            if vdf_key in self.data[year]["vdf"]:
                self.data[year]["vdf"][vdf_key] = pd.concat(
                    (self.data[year]["vdf"][vdf_key],
                     vdf_dict[vdf_key]),
                    ignore_index=True
                )
            else:
                self.data[year]["vdf"][vdf_key] = vdf_dict[vdf_key]

        # append new candidates
        self.data[year]["candidate_map"] = {
            **self.data[year]["candidate_map"], **candidate_map
        }

        # update loaded dictionary
        self.loaded[year] = self.loaded[year].union(ridings)

    def load(self, robust=True):
        """
        load and merge all data for ridings specified
        """
        for year in self.years:
            print(f"Loading year {year} . . . ", end="")
            new_ridings = utils.validate_ridings(
                list(self.ridings.difference(self.loaded[year])),
                year=year
            )
            if len(list(new_ridings)) > 0:
                self._load_all(year, new_ridings)
            print("loaded.")

        return self

    def plot_votes(self, party, year=None, plot_variable="VoteFraction",
                   ridings_args=None, basemap=None, advance=False,
                   filename=None, **kwargs):
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

        ax = viz.votes_plot(gdf_plot, party=party, gdf_ridings=gdf_ridings,
                            plot_variable=plot_variable,
                            ridings_args=ridings_args, basemap=basemap,
                            year=year, **kwargs)
        if filename is not None:
            viz.savepng(filename)
        return ax

    def plot_compare(self, party1=None, party2=None, year=None,
                     plot_variable="VoteFraction", ridings_args=None,
                     basemap=None, advance=False, filename=None, **kwargs):
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

        ax = viz.votes_comparison_plot(gdf_plot, party1=party1, party2=party2,
                                       gdf_ridings=gdf_ridings,
                                       plot_variable=plot_variable,
                                       ridings_args=ridings_args,
                                       basemap=basemap, year=year, **kwargs)
        if filename is not None:
            viz.savepng(filename)
        return ax

    def plot_multiyear(self, comparison=False, party=None, party1=None,
                       party2=None, years=None,
                       plot_variable="VoteFraction",
                       ridings_args=None, basemap=None,
                       advance=False, filename=None, **kwargs):
        if len(self.data) == 0:
            print("please load some data first")
            return None

        if years is None:
            years = self.years[-4:]

        if advance:
            gdf_vote_name = "gdf_advance"
        else:
            gdf_vote_name = "gdf_eday_merged"

        fig = viz.multiyear_plot(self, years=years, gdf_vote_name=gdf_vote_name,
                                 party=party, party1=party1, party2=party2,
                                 plot_variable=plot_variable,
                                 comparison=comparison,
                                 ridings_args=ridings_args,
                                 basemap=basemap, **kwargs)
        if filename is not None:
            viz.savepng(filename)
        return fig

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
                df = (pd.concat((self.data[year]["vdf"]["eday"],
                                 self.data[year]["vdf"]["advance"],
                                 self.data[year]["vdf"]["special"]),
                                ignore_index=True)
                      .groupby("Party")
                      .aggregate({"Votes": "sum"}))
                df["VoteFraction"] = df["Votes"] / (df["Votes"].sum())
                if key.lower() == "fraction":
                    return df.sort_values("VoteFraction", ascending=False)
                else:
                    return df.sort_values("Votes", ascending=False)

            elif by.lower() == "candidate":
                df = (pd.concat((self.data[year]["vdf"]["eday"],
                                 self.data[year]["vdf"]["advance"],
                                 self.data[year]["vdf"]["special"]),
                                ignore_index=True)
                      .get(["Party", "DistrictName",
                            "CandidateLastName", "CandidateFirstName",
                            "ElectedIndicator", "Votes"])
                      .copy())
                df["Estring"] = (df["ElectedIndicator"]
                                 .map(lambda val: ("  (Elected)"
                                                   if val == "Y" else "")))
                df["Candidate"] = (df["CandidateLastName"]
                                   + ", " + df["CandidateFirstName"]
                                   + df["Estring"])
                df = (df
                      .groupby(["Candidate", "Party", "DistrictName"])
                      .aggregate({"Votes": "sum"}))
                # sum votes by riding
                ridingsum = df.groupby(level="DistrictName").sum()
                df["VoteFraction"] = (
                    df.apply(lambda row: row["Votes"] / (ridingsum
                                                         .loc[row.name[-1],
                                                              "Votes"]),
                                                         axis=1)
                )
                if key.lower() == "fraction":
                    return df.sort_values("VoteFraction", ascending=False)
                else:
                    return df.sort_values("Votes", ascending=False)
            else:
                print("parameter 'by' must be 'Party' or 'Candidate'")
        else:
            print("please load votes data with load() or load_votes()")
        return None

    def __getitem__(self, item):
        return self.data[item]

    def __repr__(self):
        return_str = f"CanadaVotes object\n"
        return_str += f"Years:"
        for year in self.years:
            return_str += f" {year}"
        return_str += "\n"
        return_str += f"Ridings:\n"
        for rid in self.ridings:
            return_str += f"\t{rid}\n"
        return_str += "\n"
        return return_str
