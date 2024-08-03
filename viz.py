"""
-------------------------------------------------------
Routines for plotting data
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
import os
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import contextily as cx
from .utils import get_inv_riding_map
from .votes import compute_vote_fraction
from .constants import partycolours, outputdir


def savepng(filename):
    """
    save current figure to file

    Parameters
    ----------
    filename : str
        filename for figure
    """
    if not os.path.exists(outputdir):
        os.mkdir(outputdir)
    if not filename.lower().endswith(".png"):
        filename = f"{filename}.png"
    plt.savefig(os.path.join(outputdir, filename))


def poll_station_plot(gdf, title=None, **kwargs):
    """
    Plot empty outlines of poll-station zones

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        with poll-station boundary geometries
    title : str
        title for plot
    kwargs
        arguments for GeoDataFrame.plot()

    Returns
    -------
    matplotlib.Axes
    """
    axobj = gdf.plot(**kwargs)

    if title is not None:
        plt.title(title)
    return axobj


def ridings_plot(gdf_ridings, year=2021, labels=False, title=None, **kwargs):
    """
    plot ridings outlines

    Parameters
    ----------
    gdf_ridings : gpd.GeoDataFrame
        with geometries at riding level, including centroids if labels is True;
        index of dataframe should be riding numbers
    year : int
        election year for labels (since riding numbers change sometimes)
    labels : bool
        if True, add riding names at centroids
    title : str
        title for plot
    kwargs
        arguments for GeoDataFrame.plot()

    Returns
    -------
    matplotlib.Axes
    """
    axobj = gdf_ridings.plot(**kwargs)
    inv_riding_map = get_inv_riding_map(year)

    if labels:
        # add labels at centroids
        for number, row in gdf_ridings.iterrows():
            plt.text(row["centroid"].x, row["centroid"].y,
                     inv_riding_map[number], ha="center", wrap=True)

    if title is not None:
        plt.title(title)

    return axobj


def votes_plot(gdf_vote, party, gdf_ridings=None, plot_variable="VoteFraction",
               figsize=None, ridings_args=None, basemap=None, year=2021,
               **kwargs):
    """
    visualize votes for single party by polling station

    Parameters
    ----------
    gdf_vote : gpd.GeoDataFrame
        including geometry and vote information
    party : str
        name of one of the parties
    gdf_ridings : gpd.GeoDataFrame
        with riding-level geometries
    plot_variable : str
        one of "VoteFraction", "Votes", "AllVoteFraction",
               "PotentialVoteFraction"
    figsize : tuple
        size of figure
    ridings_args : dict
        parameters for ridings_plot
    basemap : str
        one of "Positron", "Voyager", "Mapnik"
    year : int
        election year (for title, riding map)
    kwargs
        keyword arguments to GeoDataFrame.plot()

    Returns
    -------
    matplotlib.pyplot.Axes
    """
    if figsize is None:
        figsize = (10, 8)

    plt.figure(figsize=figsize)

    if plot_variable not in gdf_vote.columns:
        if plot_variable == "VoteFraction":
            gdf_vote = compute_vote_fraction(gdf_vote)
        else:
            print(f"{plot_variable} not in dataframe")
            return

    if "cmap" not in kwargs:
        partycolour = partycolours.get(party, "cadetblue")
        cmap = (LinearSegmentedColormap
                .from_list("Custom", colors=["white", partycolour],
                           N=256))
    else:
        cmap = kwargs.pop("cmap")

    if basemap is not None:
        # add some transparency so the basemap shows through
        kwargs["alpha"] = 0.7

    ax = (gdf_vote
          .reset_index("DistrictName")
          .loc[party]
          .plot(column=plot_variable, legend=True, ax=plt.gca(),
                cmap=cmap, **kwargs))

    if gdf_ridings is not None:
        if ridings_args is None:
            ridings_args = {}
        ridings_args0 = {"color": "None",
                         "labels": True,
                         "linewidth": 1,
                         "edgecolor": "darkslategrey"}
        ridings_args0.update(ridings_args)
        ridings_plot(gdf_ridings, year=year, ax=ax, **ridings_args0)

    if basemap is not None:
        # add basemap from web provider
        provider = None
        if basemap == "Mapnik":
            provider = cx.providers.OpenStreetMap.Mapnik
        elif basemap == "Voyager":
            provider = cx.providers.CartoDB.Voyager
        elif basemap == "Positron":
            provider = cx.providers.CartoDB.Positron
        else:
            print("specified provider not implemented")
        if provider is not None:
            # noinspection PyTypeChecker
            cx.add_basemap(ax, crs=gdf_vote.crs, attribution=False,
                           source=provider)

    return ax


# noinspection PyTypeChecker
def votes_comparison_plot(gdf_vote, party1=None, party2=None, gdf_ridings=None,
                          plot_variable="VoteFraction", figsize=None,
                          ridings_args=None, basemap=None, year=2021,
                          **kwargs):
    """
    visualize votes difference between two parties.  If one or both parties
    not specified, remaining party or parties with highest vote share used.

    Parameters
    ----------
    gdf_vote : gpd.GeoDataFrame
        including geometry and vote information
    party1 : str
        name of first party to compare
    party2 : str
        name of second party to compare
    gdf_ridings : gpd.GeoDataFrame
        with riding-level geometries
    plot_variable : str
        one of "VoteFraction", "Votes", "AllVoteFraction",
               "PotentialVoteFraction"
    figsize : tuple
        size of figure
    ridings_args : dict
        parameters for ridings_plot
    basemap : str
        one of "Positron", "Voyager", "Mapnik"
    year : int
        election year
    kwargs
        keyword arguments to GeoDataFrame.plot()

    Returns
    -------
    matplotlib.pyplot.Axes
    """
    if figsize is None:
        figsize = (10, 8)

    plt.figure(figsize=figsize)

    if plot_variable not in gdf_vote.columns:
        print(f"{plot_variable} not in dataframe")
        return

    # if parties not specified, use parties with highest total vote share
    if party1 is None or party2 is None:
        df_party_votes = (gdf_vote
                          .reset_index()
                          .get(["Party", "Votes"])
                          .groupby("Party")
                          .sum()
                          .sort_values("Votes", ascending=False))
        party_a, party_b = df_party_votes.index[:2]
        if party1 is None:
            if party2 is None:
                party1, party2 = party_a, party_b
            elif party2 == party_a:
                party1 = party_b
            else:
                party1 = party_a
        elif party1 == party_a:
            party2 = party_b
        else:
            party2 = party_a

    # select the subsets for the two parties
    gdf1 = (gdf_vote
            .xs(level="Party", key=party1)
            .copy())

    gdf2 = (gdf_vote
            .xs(level="Party", key=party2)
            .copy())

    # check if indexes of the two party tables match (it won't if one
    # or the other party is not represented in some locations, in which case
    # the subtraction of the plot_variable will fail)
    if not gdf1.index.equals(gdf2.index):
        # compute a common index and apply it to each frame
        index_union = gdf1.index.union(gdf2.index)
        gdf1 = gdf1.reindex(index_union)
        gdf2 = gdf2.reindex(index_union)

        # fill the missing values of the plot_variable column with zeros
        gdf1[plot_variable] = gdf1[plot_variable].fillna(0)
        gdf2[plot_variable] = gdf2[plot_variable].fillna(0)

        # fill the missing geometries with the values from the other party
        gdf1["geometry"] = gdf1["geometry"].fillna(gdf2["geometry"])

    # cmopute the difference and Bob should be your uncle
    gdf1["Difference"] = gdf1[plot_variable] - gdf2[plot_variable]

    colour1 = partycolours.get(party1, "lightcoral")
    colour2 = partycolours.get(party2, "cadetblue")
    custom_cmap = (LinearSegmentedColormap
                   .from_list("Custom",
                              colors=[colour2, "white", colour1],
                              N=256))

    crange_max = gdf1["Difference"].abs().max()

    if basemap is not None:
        # add some transparency so the basemap shows through
        kwargs["alpha"] = 0.7

    ax = (gdf1
          .plot(column="Difference", legend=True, ax=plt.gca(),
                vmin=-1 * crange_max, vmax=crange_max,
                cmap=custom_cmap, **kwargs))

    if gdf_ridings is not None:
        if ridings_args is None:
            ridings_args = {}
        ridings_args0 = {"color": "None",
                         "labels": True,
                         "linewidth": 1,
                         "edgecolor": "darkslategrey"}
        ridings_args0.update(ridings_args)
        ridings_plot(gdf_ridings, year=year, ax=ax, **ridings_args0)

    # add party names to colorbar ends
    cbar = plt.gcf().axes[-1]
    cbar.text(-0.35, 1.03, s=party1.split(" ")[0].split("-")[0],
              ha='left', va='center',
              size=14, color=colour1,
              transform=cbar.transAxes)
    cbar.text(-0.35, -0.03, s=party2.split(" ")[0].split("-")[0],
              ha='left', va='center',
              size=14, color=colour2,
              transform=cbar.transAxes)
    cbar.set_title(plot_variable, y=0.5, x=3.3, va="center",
                   size=14, rotation=-90)

    if basemap is not None:

        # add basemap from web provider
        if basemap == "Mapnik":
            provider = cx.providers.OpenStreetMap.Mapnik
        elif basemap == "Voyager":
            provider = cx.providers.CartoDB.Voyager
        elif basemap == "Positron":
            provider = cx.providers.CartoDB.Positron
        else:
            print("'basemap' must be one of 'Mapnik', 'Voyager' or 'Positron'")
            return ax
        # noinspection PyTypeChecker
        cx.add_basemap(ax, crs=gdf_vote.crs, attribution=False,
                       source=provider)

    return ax
