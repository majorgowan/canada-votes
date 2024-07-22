"""
-------------------------------------------------------
Routines for plotting data
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
import matplotlib.pyplot as plt
from .utils import get_inv_riding_map


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
    matplotlib.axes
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
    matplotlib.axes
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