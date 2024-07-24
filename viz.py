"""
-------------------------------------------------------
Routines for plotting data
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from .utils import get_inv_riding_map
from .votes import compute_vote_fraction
from .constants import partycolours


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


def ridings_plot(gdf_ridings, labels=False, title=None, **kwargs):
    """
    plot ridings outlines

    Parameters
    ----------
    gdf_ridings : gpd.GeoDataFrame
        with geometries at riding level, including centroids if labels is True;
        index of dataframe should be riding numbers
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
    inv_riding_map = get_inv_riding_map()

    if labels:
        # add labels at centroids
        for number, row in gdf_ridings.iterrows():
            plt.text(row["centroid"].x, row["centroid"].y,
                     inv_riding_map[number], ha="center", wrap=True)

    if title is not None:
        plt.title(title)

    return axobj


def votes_plot(gdf_vote, party, gdf_ridings=None, plot_variable="VoteFraction",
               figsize=None, ridings_args=None, **kwargs):
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
        partycolour = partycolours.get(party, "black")
        cmap = (LinearSegmentedColormap
                .from_list("Custom",
                            colors = ["white", partycolour],
                            N=256))
    else:
        cmap = kwargs.pop("cmap")

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
                         "edgecolor": "gray"}
        ridings_args0.update(ridings_args)
        ridings_plot(gdf_ridings, ax=ax, **ridings_args0)

    return ax


def votes_comparison_plot(gdf_vote, party1, party2, gdf_ridings=None,
                          plot_variable="VoteFraction",
                          figsize=None, ridings_args=None, **kwargs):
    """
    visualize votes for single party by polling station

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
    plot_votefraction : bool
        if True, plot vote fraction, otherwise plot total votes
    figsize : tuple
        size of figure
    ridings_args : dict
        parameters for ridings_plot
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

    gdf1 = (gdf_vote
            .reset_index("DistrictName")
            .loc[party1]).copy()

    gdf2 = (gdf_vote
            .reset_index("DistrictName")
            .loc[party2])

    gdf1["Difference"] = gdf1[plot_variable] - gdf2[plot_variable]

    colour1 = partycolours[party2]
    colour2 = partycolours[party1]
    custom_cmap = (LinearSegmentedColormap
                   .from_list("Custom",
                              colors = [colour1, "white", colour2],
                              N=256))

    crange_max = gdf1["Difference"].abs().max()

    ax = (gdf1
          .plot(column="Difference", legend=True, ax=plt.gca(),
                vmin = -1 * crange_max, vmax=crange_max,
                cmap=custom_cmap, **kwargs))

    if gdf_ridings is not None:
        if ridings_args is None:
            ridings_args = {}
        ridings_args0 = {"color": "None",
                         "labels": True,
                         "linewidth": 1,
                         "edgecolor": "gray"}
        ridings_args0.update(ridings_args)
        ridings_plot(gdf_ridings, ax=ax, **ridings_args0)

    return ax
