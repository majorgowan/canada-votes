"""
-------------------------------------------------------
main program for canada votes program
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
from .constants import areas
from .utils import validate_ridings
from . import votes, geometry, viz


class CanadaVotes:
    def __init__(self, **kwargs):
        self.area = kwargs.get("area", None)
        self.ridings = kwargs.get("ridings", None)

        if self.ridings is None:
            if self.area is not None:
                self.ridings = areas.get(self.area, None)
            if self.ridings is None:
                print("please specify a valid area or list of ridings")

    def add_ridings(self, area=None, ridings=None):
        new_ridings = []
        if area is not None:
            new_ridings += areas.get(area, [])
        if ridings is not None:
            new_ridings += ridings

        invalid_ridings = validate_ridings(new_ridings)
        if invalid_ridings is not None:
            print("the following riding names are invalid:")
            for rid in invalid_ridings:
                print(f"\t{rid}")

        self.ridings += [rid for rid in new_ridings
                         if rid not in invalid_ridings]

    def load_geometries(self):
        self.gdf_eday = geometry.load_geometries(ridings=self.ridings,
                                                 advance=False)
        self.gdf_advance = geometry.load_geometries(ridings=self.ridings,
                                                    advance=True)
        self.gdf_ridings = geometry.dissolve_ridings(gdf=self.gdf_advance)

    def load_votes(self):
        self.vdf = votes.load_vote_data(ridings=self.ridings)

    def merge_votes(self):
        # election-day polls
        self.gdf_eday = geometry.merge_votes(gdf=self.gdf_eday,
                                             df_vote=self.vdf)
        # merge geometries of polls with merged counting
        self.gdf_eday_merged = (geometry
                                .combine_mergedwith_columns(self.gdf_eday))

        # advance polls
        self.gdf_advance = geometry.merge_votes(gdf=self.gdf_advance,
                                                df_vote=self.vdf)
        # add columns for election-day votes in advance poll areas
        self.gdf_advance = votes.add_eday_votes(self.gdf_eday,
                                                self.gdf_advance)

    def load(self):
        """
        load and merge all data for ridings specified
        """
        self.load_geometries()
        self.load_votes()
        self.merge_votes()

    def plot_votes(self, party, plot_variable="VoteFraction",
                   figsize=None, ridings_args=None, basemap=None,
                   advance=False, **kwargs):
        if advance:
            gdf_plot = self.gdf_advance
        else:
            gdf_plot = self.gdf_eday_merged

        viz.votes_plot(gdf_plot, party=party, gdf_ridings=self.gdf_ridings,
                       plot_variable=plot_variable, figsize=figsize,
                       ridings_args=ridings_args, basemap=basemap, **kwargs)

    def plot_compare(self, party1, party2, plot_variable="VoteFraction",
                     figsize=None, ridings_args=None, basemap=None,
                     advance=False, **kwargs):
        if advance:
            gdf_plot = self.gdf_advance
        else:
            gdf_plot = self.gdf_eday_merged

        viz.votes_comparison_plot(gdf_plot, party1=party1, party2=party2,
                                  gdf_ridings=self.gdf_ridings,
                                  plot_variable=plot_variable,
                                  figsize=figsize, ridings_args=ridings_args,
                                  basemap=basemap, **kwargs)

    def __repr__(self):
        return_str = f"CanadaVotes object\n"
        return_str += f"ridings:\n"
        for rid in self.ridings:
            return_str += f"\t{rid}\n"
        for element, description in [("gdf_advance", "Advance poll geometries"),
                                     ("gdf_eday", "Election day geometries"),
                                     ("vdf", "Votes data")]:
            return_str += f"{description}: "
            if hasattr(self, element):
                return_str += "loaded\n"
            else:
                return_str += "not loaded\n"
        return_str += "\n\n"
        return return_str