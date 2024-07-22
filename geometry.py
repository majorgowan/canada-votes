"""
-------------------------------------------------------
Routines for reading and manipulating geometry files
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
import os
import pandas as pd
import geopandas as gpd
from .constants import codeprovs, datadir, areas
from .utils import provs_from_ridings, apply_riding_map


def load_geometries(ridings=None, area=None, advance=False):
    """
    load geopandas file and select subset of ridings

    Parameters
    ----------
    ridings : list
        names of ridings to select
    area : str
        name of predefined block of ridings
    advance : bool
        if True, load geometries for advance polls

    Returns
    -------
    gpd.GeoDataFrame
        dataframe with geometries
    """
    if ridings is None:
        if area is not None:
            ridings = areas[area]
        else:
            print("please specify list of ridings or name of area")
            return
    riding_codes = apply_riding_map(ridings)

    # get list of province codes from riding numbers
    provcode_list = provs_from_ridings(ridings)

    gdf = gpd.GeoDataFrame()

    for provcode in provcode_list:
        province = codeprovs[provcode]

        if advance:
            geometry_file = f"{province}_{provcode}_geometries_adv.zip"
        else:
            geometry_file = f"{province}_{provcode}_geometries.zip"

        gdf0 = gpd.read_file(os.path.join(datadir, geometry_file))
        gdf = pd.concat((gdf, gdf0), ignore_index=True)

    gdf = gdf[gdf["FED_NUM"].isin(riding_codes)]

    return gdf


def dissolve_ridings(gdf):
    """
    combine polling station zones to whole ridings

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        dataframe with "geometries" and "FED_NUM" columns

    Returns
    -------
    gpd.GeoDataFrame
        dataframe with dissolved geometries
    """
    # join polygons of boundaries in each riding
    gdf = gdf.dissolve(by="FED_NUM")

    # switch coordinate system to extract centroid, then switch back
    gdf = gdf.to_crs(epsg=2263)
    gdf["centroid"] = gdf.centroid
    # switch back to longitude/latitude
    gdf = gdf.to_crs(epsg=4326)
    gdf["centroid"] = gdf["centroid"].to_crs(epsg=4326)

    return gdf

