"""
-------------------------------------------------------
Routines for plotting data
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
import os
import pandas as pd
import contextily as cx
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import StrMethodFormatter
from .utils import get_inv_riding_map
from .geometry import merge_geometry_into_pivot_tables
from .constants import partycolours, outputdir
from .votes import pivot_vote_tables


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


def ridings_plot(gdf_ridings, year=2021, labels=False, title=None,
                 fontsize=12, **kwargs):
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
    fontsize : int
        if labels is True, set the fontsize
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
        for _, row in gdf_ridings.iterrows():
            axobj.text(row["centroid"].x, row["centroid"].y,
                       inv_riding_map[row["FED_NUM"]],
                       fontsize=fontsize, ha="center", wrap=True)

    if title is not None:
        plt.title(title)

    return axobj


def plot_variable_to_values_column(plot_variable):
    """
    Determine values column for pivot based on the plot variable

    Parameters
    ----------
    plot_variable : str
        the variable to be plotted

    Returns
    -------
    str
    """
    if plot_variable in ["ElectionDayVotes", "ElectionDayVoteFraction"]:
        return "ElectionDayVotes"
    elif plot_variable in ["TotalVotes", "TotalVoteFraction"]:
        # only makes sense for "advance" poll data
        return "TotalVotes"
    else:
        return "Votes"


def pivot_merge_and_concat(df_vote, gdf, values_column, party):
    """
    Construct pivot tables for each district and columns for each party,
    merge geometries into all, and concatenate results

    Parameters
    ----------
    df_vote : pd.DataFrame
        with votes data
    gdf : gpd.GeoDataFrame
        with geometries for merging
    values_column : str
        column for values in pivot tables
    party : list or str
        names of parties to select

    Returns
    -------
    pd.DataFrame
    """
    df_pivots = pivot_vote_tables(df_vote, values_column=values_column)
    df_pivots = merge_geometry_into_pivot_tables(df_pivots, gdf)

    if isinstance(party, str):
        party = [party]

    # select party column and concatenate riding tables
    df_total = pd.concat(
        [df[["DistrictName", "Poll", "PD_NUM", *party,
             f"Total{values_column}", "geometry"]]
         for df in df_pivots.values()],
        ignore_index=True
    )

    return df_total


def votes_plot(df_vote, gdf, party, gdf_ridings=None,
               plot_variable="VoteFraction",
               figwidth=None, ax=None, ridings_args=None, basemap=None,
               year=2021, **kwargs):
    """
    visualize votes for single party by polling station

    Parameters
    ----------
    df_vote : pd.DataFrame
        with vote results
    gdf : gpd.GeoDataFrame
        including geometry corresponding to the supplied df_vote table
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
    values_column = plot_variable_to_values_column(plot_variable)

    if ax is None:
        if figwidth is None:
            figwidth = 12

        total_bounds = gdf.total_bounds
        aspect = ((total_bounds[3] - total_bounds[1])
                  / (total_bounds[2] - total_bounds[0]))
        figheight = aspect * figwidth

        fig = plt.figure(figsize=(figwidth, figheight))
        ax = fig.gca()

    df_total = pivot_merge_and_concat(df_vote, gdf, values_column, party)

    if plot_variable in ["VoteFraction", "ElectionDayVoteFraction",
                         "TotalVoteFraction"]:
        df_total[party] = (df_total[party]
                           .divide(df_total[f"Total{values_column}"]))

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

    ax = (df_total
          .plot(column=party, legend=True, ax=ax,
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

    # don't really need to know latitude and longitude values!
    ax.set_xticks([])
    ax.set_yticks([])

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
            cx.add_basemap(ax, crs=gdf.crs, attribution=False,
                           source=provider)

    return ax


def make_party_comparison_df(df_vote, gdf, party1, party2,
                             plot_variable):
    """
    Produce dataframe with columns for two parties with values

    Parameters
    ----------
    df_vote : pd.DataFrame
        unpivoted votes data table
    gdf : gpd.GeoDataFrame
        with geometries (to merge into vote pivots)
    party1 : str
        first party to compare
    party2 : str
        second party to compare
    plot_variable : str
        one of "VoteFraction", "Votes", "AllVoteFraction",
               "PotentialVoteFraction"

    Returns
    -------
    pd.DataFrame
        table with columns for each party
    """
    values_column = plot_variable_to_values_column(plot_variable)

    df_total = pivot_merge_and_concat(df_vote, gdf, values_column,
                                      [party1, party2])

    if "Fraction" in plot_variable:
        # normalize values by total
        df_total[party1] = (
            df_total[party1]
            .divide(df_total[f"Total{values_column}"])
        )
        df_total[party2] = (
            df_total[party2]
            .divide(df_total[f"Total{values_column}"])
        )

    df_total["Difference"] = (df_total[party1] - df_total[party2])

    return df_total


# noinspection PyTypeChecker
def votes_comparison_plot(df_vote, gdf, party1=None, party2=None,
                          gdf_ridings=None, plot_variable="VoteFraction",
                          figwidth=None, ax=None, ridings_args=None,
                          basemap=None, year=2021, crange_max=None,
                          smalltext=False, **kwargs):
    """
    visualize votes difference between two parties.  If one or both parties
    not specified, remaining party or parties with the highest vote share used.

    Parameters
    ----------
    df_vote : pd.DataFrame
        with vote results
    gdf : gpd.GeoDataFrame
        including geometry corresponding to the supplied df_vote table
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
    smalltext : bool
        set to True for smaller and spacier labels
    kwargs
        keyword arguments to GeoDataFrame.plot()

    Returns
    -------
    matplotlib.pyplot.Axes
    """
    if ax is None:
        if figwidth is None:
            figwidth = 12

        total_bounds = gdf.total_bounds
        aspect = ((total_bounds[3] - total_bounds[1])
                  / (total_bounds[2] - total_bounds[0]))
        figheight = aspect * figwidth

        fig = plt.figure(figsize=(figwidth, figheight))
        ax = fig.gca()

    if party2 is None:
        df_most_votes = (df_vote
                         .loc[df_vote["Party"] != party1, ["Party", "Votes"]]
                         .groupby("Party")
                         .sum()
                         .sort_values("Votes", ascending=False))
        if party1 is None:
            party1 = df_most_votes.index[0]
            party2 = df_most_votes.index[1]
        else:
            party2 = df_most_votes.index[0]

    df_total = make_party_comparison_df(df_vote, gdf, party1, party2,
                                        plot_variable)

    colour1 = partycolours.get(party1, "lightcoral")
    colour2 = partycolours.get(party2, "cadetblue")
    custom_cmap = (LinearSegmentedColormap
                   .from_list("Custom",
                              colors=[colour2, "white", colour1],
                              N=256))

    if crange_max is None:
        crange_max = df_total["Difference"].abs().max()

    if basemap is not None:
        # add some transparency so the basemap shows through
        kwargs["alpha"] = 0.7

    ax = (df_total
          .plot(column="Difference", legend=True,
                vmin=-1 * crange_max, vmax=crange_max,
                cmap=custom_cmap, ax=ax, **kwargs))

    if smalltext:
        cbar_text_size = 10
        cbar_ticklabel_size = 8
        cbar_label_x = 5.6
        cbar_end_pos = 0.07
        label_fontsize = 9
    else:
        cbar_text_size = 12
        cbar_ticklabel_size = 12
        cbar_label_x = 3.3
        cbar_end_pos = 0.05
        label_fontsize = 12

    if gdf_ridings is not None:

        if ridings_args is None:
            ridings_args = {}
        ridings_args0 = {"color": "None",
                         "labels": True,
                         "linewidth": 1,
                         "edgecolor": "darkslategrey"}
        ridings_args0.update(ridings_args)
        ridings_plot(gdf_ridings, year=year, ax=ax,
                     fontsize=label_fontsize, **ridings_args0)

    # don't really need to know latitude and longitude values!
    ax.set_xticks([])
    ax.set_yticks([])

    # add party names to colorbar ends
    cbar = plt.gcf().axes[-1]
    cbar.text(-0.35, 1 + cbar_end_pos, s=party1.split(" ")[0].split("-")[0],
              ha='left', va='center',
              size=cbar_text_size, color=colour1,
              transform=cbar.transAxes)
    cbar.text(-0.35, -1 * cbar_end_pos, s=party2.split(" ")[0].split("-")[0],
              ha='left', va='center',
              size=cbar_text_size, color=colour2,
              transform=cbar.transAxes)
    cbar.set_title(plot_variable, y=0.5, x=cbar_label_x, va="center",
                   size=cbar_text_size, rotation=-90)
    cbar.tick_params(axis='y', which='major', labelsize=cbar_ticklabel_size)
    cbar.yaxis.set_major_formatter(StrMethodFormatter('{x:.2f}'))

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
        cx.add_basemap(ax, crs=gdf.crs, attribution=False,
                       source=provider)

    return ax


# noinspection PyTypeChecker
def multiyear_plot(canadavotes, years, name, party=None,
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
    name : str
        name of table to use for plots ("eday_merged" or "advance")
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
    # TODO: make single colorbar for all panels

    # get total longitude and latitude ranges
    total_bounds = canadavotes[years[0]]["gdf"]["ridings"].total_bounds
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
    min_val = 1e10
    max_val = -1e10

    if comparison:
        for year in years:
            df_vote1 = canadavotes[year]["vdf"][name]
            gdf1 = canadavotes[year]["gdf"][name]
            df_total = make_party_comparison_df(df_vote1, gdf1, party1, party2,
                                                plot_variable)
            max_val = max(df_total["Difference"].abs().max(), max_val)

    else:

        values_column = plot_variable_to_values_column(plot_variable)

        for year in years:
            df_vote1 = canadavotes[year]["vdf"][name]
            gdf1 = canadavotes[year]["gdf"][name]
            df_total = pivot_merge_and_concat(df_vote1, gdf1,
                                              values_column, party)

            if "Fraction" in plot_variable:
                df_total[party] = (df_total[party]
                                   .divide(df_total[f"Total{values_column}"]))

            min_val = min(df_total[party].min(), min_val)
            max_val = max(df_total[party].max(), max_val)

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
            votes_comparison_plot(
                df_vote=canadavotes[year]["vdf"][name],
                gdf=canadavotes[year]["gdf"][name],
                party1=party1, party2=party2,
                gdf_ridings=canadavotes[year]["gdf"]["ridings"],
                plot_variable=plot_variable,
                ax=axs[row][col],
                ridings_args=ridings_args, basemap=basemap,
                year=year, crange_max=max_val, smalltext=True,
                **kwargs)
        else:
            votes_plot(df_vote=canadavotes[year]["vdf"][name],
                       gdf=canadavotes[year]["gdf"][name],
                       party=party,
                       gdf_ridings=canadavotes[year]["gdf"]["ridings"],
                       plot_variable=plot_variable,
                       ax=axs[row][col],
                       ridings_args=ridings_args, basemap=basemap,
                       year=year, vmin=min_val, vmax=max_val,
                       **kwargs)

        # position title inside top-left (election year)
        axs[row][col].set_title(f"{year}", fontsize=13, loc="left",
                                x=0.03, y=0.86)

        col += 1

    if ncols > 1:
        plt.subplots_adjust(hspace=0.3)

    return fig
