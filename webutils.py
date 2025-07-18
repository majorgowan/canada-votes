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
    if advance:
        gdf = (cdvobj.data[year]["gdf_advance"]
               .get(["FED_NUM", "Poll",
                     "geometry", "DistrictNumber",
                     "CandidateLastName", "CandidateMiddleName",
                     "CandidateFirstName", "Votes", "ElectionDayVotes"])
               .rename(columns={"Votes": "AdvanceVotes"})
               .reset_index().copy())
    else:
        gdf = (cdvobj[year]["gdf_eday_merged"]
               .get(["FED_NUM", "Poll",
                     "geometry", "DistrictNumber",
                     "CandidateLastName", "CandidateMiddleName",
                     "CandidateFirstName", "Votes"])
               .reset_index().copy())

    gdf_ridings = cdvobj.data[year]["gdf_ridings"]
    # add district names
    gdf_ridings["DistrictName"] = (gdf_ridings
                                   .index.map(get_inv_riding_map(year)))

    # create json map from riding to party to condidates
    candidate_map = {}
    candidate_df = (gdf[["FED_NUM", "Party",
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

    # make map from riding to party to special votes
    vdf = cdvobj.data[year]["vdf"].copy()
    special_dict = (vdf[vdf["Poll"].str.startswith(" S")]
                    .get(["DistrictNumber", "Party", "Votes"])
                    .groupby(["DistrictNumber", "Party"])
                    .sum()
                    .to_dict()["Votes"])
    special_map = {fednum: {party: special_dict[(fn, party)]
                            for (fn, party) in special_dict
                            if fn == fednum}
                   for fednum in vdf["DistrictNumber"].unique()}
    if not advance:
        advance_dict = (vdf[vdf["Poll"].str.match(r"^ 6[0-9]{2}")]
                        .get(["DistrictNumber", "Party", "Votes"])
                        .groupby(["DistrictNumber", "Party"])
                        .sum()
                        .to_dict()["Votes"])
        advance_map = {fednum: {party: advance_dict[(fn, party)]
                                for (fn, party) in advance_dict
                                if fn == fednum}
                       for fednum in vdf["DistrictNumber"].unique()}

    # make "pivoted" frames with columns for each candidate in each riding
    if advance:
        pivoted_advance_gdfs = {}

    pivoted_eday_gdfs = {}
    for fed_num in gdf["FED_NUM"].unique():
        gdfa = gdf[gdf["FED_NUM"] == fed_num]

        if advance:
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

        else:
            pivoted_eday_gdfs[fed_num] = (
                gdfa[["PD_NUM", "DistrictName", "Poll", "geometry", "Party",
                      "Votes"]]
                .pivot(index=["DistrictName", "PD_NUM", "Poll", "geometry"],
                       columns="Party", values="Votes").reset_index()
            )

            pivoted_eday_gdfs[fed_num].columns.name = None
            pivoted_eday_gdfs[fed_num]["TotalVotes"] = (
                pivoted_eday_gdfs[fed_num].iloc[:, 4:].sum(axis=1)
            )

    # build one big json!
    leaflet_data = {"polldata": {}}
    for fed_num in pivoted_eday_gdfs.keys():
        if advance:
            advance_dict = (gpd.GeoDataFrame(pivoted_advance_gdfs[fed_num])
                            .to_geo_dict(drop_id=True))
        eday_dict = (gpd.GeoDataFrame(pivoted_eday_gdfs[fed_num])
                     .to_geo_dict(drop_id=True))
        for poll in range(len(eday_dict["features"])):
            for property in eday_dict["features"][poll]["properties"]:
                if property not in ["DistrictName", "PD_NUM", "Poll"]:
                    feature_dict = {
                        "eday": (eday_dict["features"][poll]["properties"]
                                 .get(property))
                    }
                    if advance:
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
            "candidates": candidate_map[fed_num],
            "special_votes": special_map[fed_num]
        }
        if not advance:
            leaflet_data["polldata"][str(fed_num)]["advance_votes"] \
                = advance_map[fed_num]

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
