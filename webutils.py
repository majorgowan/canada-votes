"""
-------------------------------------------------------
Utility functions for canadavotes webpage
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
import os
import geopandas as gpd

from .constants import outputdir
from .votes import pivot_vote_tables
from .utils import get_inv_riding_map, write_json
from .geometry import merge_geometry_into_pivot_tables
from .ontario import make_ontario_riding_map, pivot_and_merge_geometries


def write_leaflet_data(cdvobj, year, filename, advance=True):
    """
    Write json file readable by the web app for building Leaflet maps

    Parameters
    ----------
    cdvobj : CanadaVotes object
    year : int
        election year for which to write data
    filename : str
        filename to write
    advance : bool
        if True, write advance-poll geometry data (including eday votes),
        otherwise election-day (only eday votes)
    """
    candidate_map = cdvobj[year]["candidate_map"]

    # get ridings table
    gdf_ridings = cdvobj[year]["gdf"]["ridings"].copy()
    # add district names
    gdf_ridings["DistrictName"] = (gdf_ridings["FED_NUM"]
                                   .map(get_inv_riding_map(year)))
    # list of district numbers
    fed_nums = gdf_ridings["FED_NUM"].unique()
    inv_riding_map = {row["FED_NUM"]: row["DistrictName"]
                      for _, row in gdf_ridings.iterrows()}

    # make map from riding to party to special votes
    special_dict = (cdvobj[year]["vdf"]["special"]
                    .get(["DistrictNumber", "Party", "Votes"])
                    .groupby(["DistrictNumber", "Party"])
                    .sum()
                    .to_dict()["Votes"])
    special_map = {fednum: {party: special_dict[(fn, party)]
                            for (fn, party) in special_dict
                            if fn == fednum}
                   for fednum in fed_nums}
    # election day viewer shows advance vote totals by riding
    advance_dict = (cdvobj[year]["vdf"]["advance"]
                    .get(["DistrictNumber", "Party", "Votes"])
                    .groupby(["DistrictNumber", "Party"])
                    .sum()
                    .to_dict()["Votes"])
    advance_map = {fednum: {party: advance_dict[(fn, party)]
                            for (fn, party) in advance_dict
                            if fn == fednum}
                   for fednum in fed_nums}

    # make "pivoted" frames with columns for each candidate in each riding
    # separate pivot tables for election-day (pooled from polling divs)
    # and advance votes and merge geometries accordingly
    if advance:
        pivoted_advance_vdfs = pivot_vote_tables(
            cdvobj[year]["vdf"]["advance"],
            values_column="Votes"
        )
        pivoted_advance_vdfs = merge_geometry_into_pivot_tables(
            pivoted_advance_vdfs, cdvobj[year]["gdf"]["advance"]
        )
        pivoted_eday_vdfs = pivot_vote_tables(
            cdvobj[year]["vdf"]["advance"],
            values_column="ElectionDayVotes"
        )
        pivoted_eday_vdfs = merge_geometry_into_pivot_tables(
            pivoted_eday_vdfs, cdvobj[year]["gdf"]["advance"]
        )
    else:
        # only election-day data available at polling-div level
        pivoted_eday_vdfs = pivot_vote_tables(
            cdvobj[year]["vdf"]["eday_merged"],
            values_column="Votes"
        )
        pivoted_eday_vdfs = merge_geometry_into_pivot_tables(
            pivoted_eday_vdfs, cdvobj[year]["gdf"]["eday_merged"]
        )
        pivoted_advance_vdfs = None

    # build one big json!
    leaflet_data = {"polldata": {}}
    for fed_num in pivoted_eday_vdfs.keys():
        if advance:
            advance_dict = (gpd.GeoDataFrame(pivoted_advance_vdfs[fed_num])
                            .to_geo_dict(drop_id=True))
        else:
            advance_dict = None
        eday_dict = (
            gpd.GeoDataFrame(
                pivoted_eday_vdfs[fed_num]
                .rename(columns={"TotalElectionDayVotes": "TotalVotes"})
            ).to_geo_dict(drop_id=True)
        )
        for poll in range(len(eday_dict["features"])):
            for property in eday_dict["features"][poll]["properties"]:
                if property not in ["DistrictName", "PD_NUM",
                                    "ADV_POLL_N", "Poll"]:
                    # votes in eday poll division, or
                    # pooled eday votes in the advance-poll division
                    feature_dict = {
                        "eday": (eday_dict["features"][poll]["properties"]
                                 .get(property))
                    }
                    if advance:
                        # advance votes in the poll division
                        feature_dict["advance"] = (
                            advance_dict["features"][poll]["properties"]
                            .get(property)
                        )
                        feature_dict["total"] = (
                            (advance_dict["features"][poll]["properties"]
                             .get(property)
                            + (eday_dict["features"][poll]["properties"]
                               .get(property)))
                        )
                    eday_dict["features"][poll]["properties"][property] \
                        = feature_dict

        leaflet_data["polldata"][str(fed_num)] = {
            "votes": eday_dict,
            "district_name": inv_riding_map[fed_num],
            "candidates": candidate_map[fed_num],
            # riding-level totals of special and advance votes
            "special_votes": special_map[fed_num],
            "advance_votes": advance_map[fed_num]
        }

    # separate boundaries and centroids from ridings frame
    # (geojson format only supports one geometry-like column)
    leaflet_data["ridings"] = gdf_ridings.drop("centroid", axis=1).to_geo_dict()
    leaflet_data["riding_centroids"] = (gdf_ridings.drop("geometry", axis=1)
                                       .rename(columns={"centroid": "geometry"})
                                       .to_geo_dict())

    # get centroid of full area (the "CRS" stuff is to get correct centroid
    # et surtout d'eviter les Warnings)
    centroid = (gdf_ridings
                .dissolve()
                .to_crs(crs=3857)["geometry"]
                .centroid
                .to_crs(crs=4326)[0])
    leaflet_data["centroid"] = {"longitude": centroid.x,
                                "latitude": centroid.y}

    write_json(leaflet_data,
               filename=os.path.join(outputdir, filename),
               indent=2)


def write_leaflet_data_ontario(ovobj, year, filename):
    """
    Write json file readable by the web app for building Leaflet maps

    Parameters
    ----------
    ovobj : OntarioVotes object
    year : int
        election year for which to write data
    filename : str
        filename to write
    """
    candidate_map = ovobj[year]["candidate_map"]

    # get ridings table
    gdf_ridings = ovobj[year]["gdf"]["ridings"].copy()
    # add district names to riding table
    inv_riding_map = make_ontario_riding_map(ovobj[year]["vdf"]["votes"],
                                             inverse=False)
    gdf_ridings["DistrictName"] = (gdf_ridings["DistrictNumber"]
                                   .map(inv_riding_map))

    # list of district numbers
    dist_nums = gdf_ridings["DistrictNumber"].unique()

    advance_dict = (ovobj[year]["vdf"]["votes"]
                    .loc[(ovobj[year]["vdf"]["votes"]["PollNumber"]
                          .str.contains("ADV"))]
                    .get(["DistrictNumber", "Party", "Votes"])
                    .groupby(["DistrictNumber", "Party"])
                    .sum()
                    .to_dict()["Votes"])
    advance_map = {dist_num: {party: advance_dict[(dn, party)]
                              for (dn, party) in advance_dict
                              if dn == dist_num}
                   for dist_num in dist_nums}

    # make "pivoted" frames with columns for each candidate in each riding
    # separate pivot tables and merge geometries accordingly
    pivoted_vdfs = pivot_and_merge_geometries(
        ovobj[year]["vdf"]["votes"],
        ovobj[year]["gdf"]["stations"],
        normalize=False
    )

    # build one big json!
    leaflet_data = {"polldata": {}}
    for dist_num in pivoted_vdfs.keys():
        eday_dict = (
            gpd.GeoDataFrame(
                pivoted_vdfs[dist_num]
            ).to_geo_dict(drop_id=True)
        )
        for poll in range(len(eday_dict["features"])):
            for property in eday_dict["features"][poll]["properties"]:
                if property not in ["DistrictNumber",
                                    "DistrictName", "PD_NUM",
                                    "PollNumber"]:
                    # votes in eday poll division
                    feature_dict = {
                        "eday": (eday_dict["features"][poll]["properties"]
                                 .get(property))
                    }
                    eday_dict["features"][poll]["properties"][property] \
                        = feature_dict

        leaflet_data["polldata"][str(dist_num)] = {
            "votes": eday_dict,
            "district_name": inv_riding_map[dist_num],
            "candidates": candidate_map[dist_num],
            "advance_votes": advance_map[dist_num]
        }

    # separate boundaries and centroids from ridings frame
    # (geojson format only supports one geometry-like column)
    leaflet_data["ridings"] = gdf_ridings.drop("centroid", axis=1).to_geo_dict()
    leaflet_data["riding_centroids"] = (gdf_ridings.drop("geometry", axis=1)
                                        .rename(columns={"centroid": "geometry"})
                                        .to_geo_dict())

    write_json(leaflet_data,
               filename=os.path.join(outputdir, filename),
               indent=2)
