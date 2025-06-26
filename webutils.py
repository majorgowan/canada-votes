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
from .utils import get_inv_riding_map, write_json


def write_leaflet_data(cdvobj, year, filename):
    """
    Write json file readable by the web app for building Leaflet maps

    Parameters
    ----------
    cdvobj : CanadaVotes object
    year : int
        election year for which to write data
    filename : str
        filename to write
    """
    gdf_ridings = cdvobj.data[year]["gdf_ridings"]
    # add district names
    gdf_ridings["DistrictName"] = (gdf_ridings
                                   .index.map(get_inv_riding_map(year)))

    # simplify data
    gdf_advance = (cdvobj.data[year]["gdf_advance"]
                   .get(["FED_NUM",
                         "geometry", "DistrictNumber",
                         "CandidateLastName", "CandidateMiddleName",
                         "CandidateFirstName", "Votes", "ElectionDayVotes"])
                   .rename(columns={"Votes": "AdvanceVotes"})
                   .reset_index().copy())

    # deduplicate Party column for independent candidates
    mask = gdf_advance[gdf_advance["Party"] == "Independent"].index
    gdf_advance.loc[mask, "Party"] = (
            "Independent_" + gdf_advance.loc[mask, "CandidateLastName"]
            + "_" + gdf_advance.loc[mask, "CandidateFirstName"]
    )

    # create json map from riding to party to condidates
    candidate_map = {}
    candidate_df = (gdf_advance[["FED_NUM", "Party",
                                 "CandidateFirstName", "CandidateMiddleName",
                                 "CandidateLastName"]]
                    .drop_duplicates())
    for fed_num, grp in candidate_df.groupby("FED_NUM"):
        grp = grp.drop("FED_NUM", axis=1)
        candidate_map[fed_num] = {}
        for party, candidate_row in grp.set_index("Party").iterrows():
            candidate_map[fed_num][party] = (
                    candidate_row["CandidateFirstName"] + " "
                    + candidate_row["CandidateLastName"]
            )

    # make "pivoted" frames with columns for each candidate in each riding
    pivoted_advance_gdfs = {}
    pivoted_eday_gdfs = {}
    for fed_num in gdf_advance["FED_NUM"].unique():
        gdfa = gdf_advance[gdf_advance["FED_NUM"] == fed_num]
        pivoted_advance_gdfs[fed_num] = (
            gdfa[["PD_NUM", "DistrictName", "geometry", "Party",
                  "AdvanceVotes"]]
            .pivot(index=["DistrictName", "PD_NUM", "geometry"],
                   columns="Party", values="AdvanceVotes").reset_index()
        )
        pivoted_advance_gdfs[fed_num].columns.name = None
        pivoted_advance_gdfs[fed_num]["TotalVotes"] = (
            pivoted_advance_gdfs[fed_num].iloc[:, 3:].sum(axis=1)
        )
        pivoted_eday_gdfs[fed_num] = (
            gdfa[["PD_NUM", "DistrictName", "geometry", "Party",
                  "ElectionDayVotes"]]
            .pivot(index=["DistrictName", "PD_NUM", "geometry"],
                   columns="Party", values="ElectionDayVotes").reset_index()
        )
        pivoted_eday_gdfs[fed_num].columns.name = None
        pivoted_eday_gdfs[fed_num]["TotalVotes"] = (
            pivoted_eday_gdfs[fed_num].iloc[:, 3:].sum(axis=1)
        )

    # build one big json!
    leaflet_data = {"polldata": {}}
    for fed_num in pivoted_advance_gdfs.keys():
        riding_dict = (gpd.GeoDataFrame(pivoted_advance_gdfs[fed_num])
                       .to_geo_dict(drop_id=True))
        eday_dict = (gpd.GeoDataFrame(pivoted_eday_gdfs[fed_num])
                     .to_geo_dict(drop_id=True))
        for poll in range(len(riding_dict["features"])):
            for property in riding_dict["features"][poll]["properties"]:
                if property not in ["DistrictName", "PD_NUM"]:
                    riding_dict["features"][poll]["properties"][property] = {
                        "advance": (riding_dict["features"][poll]["properties"]
                                    .get(property)),
                        "eday": (eday_dict["features"][poll]["properties"]
                                 .get(property)),
                        "total": (riding_dict["features"][poll]["properties"]
                                  .get(property)
                                  + (eday_dict["features"][poll]["properties"]
                                     .get(property)))
                    }
        leaflet_data["polldata"][str(fed_num)] = {
            "votes": riding_dict,
            "candidates": candidate_map[fed_num]
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
