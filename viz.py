"""
-------------------------------------------------------
Routines for plotting data
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
import os
import contextily as cx
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from .utils import get_inv_riding_map, party_difference
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
            axobj.text(row["centroid"].x, row["centroid"].y,
                       inv_riding_map[number], ha="center", wrap=True)

    if title is not None:
        plt.title(title)

    return axobj


def votes_plot(gdf_vote, party, gdf_ridings=None, plot_variable="VoteFraction",
               figwidth=None, ax=None, ridings_args=None, basemap=None,
               year=2021, **kwargs):
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
    figwidth : float
        width of figure
    ax : matplotlib.Axes object
        existing Axes into which to plot figure
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
    if ax is None:
        if figwidth is None:
            figwidth = 12

        total_bounds = gdf_vote.total_bounds
        aspect = ((total_bounds[3] - total_bounds[1])
                  / (total_bounds[2] - total_bounds[0]))
        figheight = aspect * figwidth

        fig = plt.figure(figsize=(figwidth, figheight))
        ax = fig.gca()

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
          .plot(column=plot_variable, legend=True, ax=ax,
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
                          plot_variable="VoteFraction", figwidth=None,
                          ax=None, ridings_args=None, basemap=None, year=2021,
                          crange_max=None, **kwargs):
    """
    visualize votes difference between two parties.  If one or both parties
    not specified, remaining party or parties with the highest vote share used.

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
    figwidth : float
        width of figure
    ax : matplotlib.Axes object
        existing Axes into which to plot figure
    ridings_args : dict
        parameters for ridings_plot
    basemap : str
        one of "Positron", "Voyager", "Mapnik"
    year : int
        election year
    crange_max : float
        value of plot_variable to correspond to maximum of colour scale
    kwargs
        keyword arguments to GeoDataFrame.plot()

    Returns
    -------
    matplotlib.pyplot.Axes
    """
    if ax is None:
        if figwidth is None:
            figwidth = 12

        total_bounds = gdf_vote.total_bounds
        aspect = ((total_bounds[3] - total_bounds[1])
                  / (total_bounds[2] - total_bounds[0]))
        figheight = aspect * figwidth

        fig = plt.figure(figsize=(figwidth, figheight))
        ax = fig.gca()

    if plot_variable not in gdf_vote.columns:
        print(f"{plot_variable} not in dataframe")
        return

    # if parties not specified, use parties with the highest total vote share
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

    # select part of gdf_vote for party1 with extra column for difference
    # to party2
    gdf1 = party_difference(gdf_vote=gdf_vote, plot_variable=plot_variable,
                            party1=party1, party2=party2)

    colour1 = partycolours.get(party1, "lightcoral")
    colour2 = partycolours.get(party2, "cadetblue")
    custom_cmap = (LinearSegmentedColormap
                   .from_list("Custom",
                              colors=[colour2, "white", colour1],
                              N=256))

    if crange_max is None:
        crange_max = gdf1["Difference"].abs().max()

    if basemap is not None:
        # add some transparency so the basemap shows through
        kwargs["alpha"] = 0.7

    ax = (gdf1
          .plot(column="Difference", legend=True,
                vmin=-1 * crange_max, vmax=crange_max,
                cmap=custom_cmap, ax=ax, **kwargs))

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


# noinspection PyTypeChecker
def multiyear_plot(canadavotes, years, gdf_vote_name, party=None,
                   party1=None, party2=None, comparison=False,
                   plot_variable="VoteFraction", figwidth=12,
                   ridings_args=None, basemap=None, **kwargs):
    """
    multi-panel plot of votes or vote comparison over multiple elections

    Parameters
    ----------
    canadavotes : CanadaVotes
        loaded CanadaVotes object
    years : list
        election years to compare
    gdf_vote_name : str
        name of GeoDataFrame to use for plots
    party : str
        name of party for simple plot
    party1 : str
        name of first party for comparison plot
    party2 : str
        name of second party for comparison plot
    comparison : bool
        if True, supply party1 and party2 for comparison plot
    plot_variable : str
        one of "VoteFraction", "Votes", "AllVoteFraction",
               "PotentialVoteFraction"
    figwidth : float
        width of entire figure
    ridings_args : dict
        parameters for ridings_plot
    basemap : str
        one of "Positron", "Voyager", "Mapnik"
    kwargs
        keyword arguments to GeoDataFrame.plot()

    Returns
    -------
    matplotlib.pyplot.Axes
    """
    # get total longitude and latitude ranges
    total_bounds = canadavotes[years[0]]["gdf_advance"].total_bounds
    aspect = ((total_bounds[3] - total_bounds[1])
              / (total_bounds[2] - total_bounds[0]))

    if len(years) <= 3:
        nrows = 1
        ncols = len(years)
    elif len(years) == 4:
        nrows = 2
        ncols = 2
    else:
        nrows = 2
        ncols = 3

    figheight = nrows * aspect * figwidth / ncols

    # the following is to determine a common range of volues for
    # all plots based on ranges for all years
    min_val = 1e9
    max_val = -1e9
    if comparison:
        for year in years:
            gdf_vote = canadavotes[year][gdf_vote_name]
            gdf1 = party_difference(gdf_vote, plot_variable,
                                    party1, party2)
            max_val = max(gdf1["Difference"].abs().max(), max_val)
    else:
        for year in years:
            gdf_vote = canadavotes[year][gdf_vote_name]
            min_val = min(gdf_vote[plot_variable].min(), min_val)
            max_val = max(gdf_vote[plot_variable].max(), max_val)

    fig, axs = plt.subplots(nrows=nrows, ncols=ncols,
                            figsize=(figwidth, figheight))

    # if only one row, make it a list to simplify below
    if nrows == 1:
        axs = [axs]

    row = 0
    col = 0
    for year in years:
        if col == ncols:
            col = 0
            row += 1

        if comparison:
            votes_comparison_plot(gdf_vote=canadavotes[year][gdf_vote_name],
                                  party1=party1, party2=party2,
                                  gdf_ridings=canadavotes[year]["gdf_ridings"],
                                  plot_variable=plot_variable,
                                  ax=axs[row][col],
                                  ridings_args=ridings_args, basemap=basemap,
                                  year=year, crange_max=max_val,
                                  **kwargs)
        else:
            votes_plot(gdf_vote=canadavotes[year][gdf_vote_name],
                       party=party,
                       gdf_ridings=canadavotes[year]["gdf_ridings"],
                       plot_variable=plot_variable,
                       ax=axs[row][col],
                       ridings_args=ridings_args, basemap=basemap,
                       year=year, vmin=min_val, vmax=max_val,
                       **kwargs)

        axs[row][col].set_title(f"{year}", fontsize=14)

        col += 1

    return fig
