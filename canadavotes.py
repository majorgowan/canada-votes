"""
-------------------------------------------------------
main program for canada votes program
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
from copy import copy
from .utils import validate_ridings
from .constants import areas
from . import votes, geometry, viz


class CanadaVotes:
    def __init__(self, years=2021, **kwargs):
        self.ridings = kwargs.get("ridings", None)
        self.years = years

        # if years is a single year, set it to a list of length 1
        if isinstance(self.years, int):
            self.years = [years]

        for year in self.years:
            if year not in [2008, 2011, 2015, 2019, 2021]:
                print("year {year} invalid")
                print("year must be one of: 2008, 2011, 2015, 2019, 2021")
                return

        if self.ridings is None:
            area = kwargs.get("area", None)
            if area is not None:
                self.ridings = copy(areas.get(area, []))
            if self.ridings is None:
                print("please specify a valid area or list of ridings")

        # initialize data to empty dictionary
        self.data = {}

    def add_ridings(self, area=None, ridings=None):
        new_ridings = []
        if area is not None:
            new_ridings += copy(areas.get(area, []))
        if ridings is not None:
            new_ridings += ridings

        self.ridings += [rid for rid in new_ridings
                         if rid not in self.ridings]

        return self

    def load_geometries(self, year, robust=False):
        ridings = validate_ridings(ridings=self.ridings, year=year)
        self.data[year]["gdf_eday"] = (geometry
                                       .load_geometries(ridings=ridings,
                                                        year=year,
                                                        advance=False))
        gdf_advance = geometry.load_geometries(ridings=ridings,
                                               year=year,
                                               advance=True)
        self.data[year]["gdf_advance"] = gdf_advance
        self.data[year]["gdf_ridings"] = (geometry
                                          .dissolve_ridings(gdf=gdf_advance,
                                                            robust=robust))
        return self

    def load_votes(self, year):
        ridings = validate_ridings(ridings=self.ridings, year=year)
        self.data[year]["vdf"] = votes.load_vote_data(ridings=ridings,
                                                      year=year)
        return self

    def merge_votes(self, year, robust=False):
        # election-day polls
        self.data[year]["gdf_eday"] = (
            geometry.merge_votes(gdf=self.data[year]["gdf_eday"],
                                 df_vote=self.data[year]["vdf"])
        )

        # merge geometries of polls with merged counting
        self.data[year]["gdf_eday_merged"] = (
            geometry.combine_mergedwith_columns(self.data[year]["gdf_eday"],
                                                robust=robust)
        )

        # advance polls
        self.data[year]["gdf_advance"] = (
            geometry.merge_votes(gdf=self.data[year]["gdf_advance"],
                                 df_vote=self.data[year]["vdf"])
        )

        # add columns for election-day votes in advance poll areas
        self.data[year]["gdf_advance"] = (
            votes.add_eday_votes(self.data[year]["gdf_eday"],
                                 self.data[year]["gdf_advance"])
        )

        return self

    def load(self, robust=False):
        """
        load and merge all data for ridings specified
        """
        for year in self.years:
            if year not in self.data:
                self.data[year] = {}
            print(f"loading year {year} . . .")
            self.load_geometries(year=year, robust=robust)
            self.load_votes(year=year)
            self.merge_votes(year=year, robust=robust)
            print("                        Loaded.")
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
        if year not in self.data:
            print("please load data first with load() or load_votes()")
            return None
        return sorted(self.data[year]["vdf"]["Party"].unique().tolist())

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
                      .get(["Candidate", "Party", "DistrictName",
                            "CandidateLastName", "CandidateFirstName",
                            "ElectedIndicator", "Votes", "TotalVotes"]))
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
            return_str += f"Election year {year}:\n"
            for element, description in [("gdf_advance",
                                          "Advance poll geometries"),
                                         ("gdf_eday",
                                          "Election day geometries"),
                                         ("vdf", "Votes data")]:
                return_str += f"{description}: "
                if element in self.data[year]:
                    return_str += "loaded\n"
                else:
                    return_str += "not loaded\n"
            if "vdf" in self.data[year]:
                return_str += f"Parties:\n"
                for party in self.parties(year):
                    return_str += f"\t{party}\n"
        return_str += "\n"
        return return_str
