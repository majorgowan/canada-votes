"""
-------------------------------------------------------
Routines for fetching data files from the internet
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
import os
import requests
from urllib.parse import urljoin
from .constants import datadir, provcodes
from .utils import update_riding_map_file


def download_file(fileurl, prefix="", overwrite=False):
    """
    Download a file in chunks

    Parameters
    ----------
    fileurl : str
        address of file to download
    prefix : str
        string to prepend to local filename (e.g. election year)
    overwrite : bool
        if False (default), do not overwrite existing file

    Returns
    -------
    str
        local filename
    """
    # if datadir doesn't exist, create it
    if not os.path.exists(datadir):
        os.mkdir(datadir)

    filename = fileurl.split("/")[-1]
    localpath = os.path.join(datadir, f"{prefix}{filename}")

    if not overwrite:
        if os.path.exists(localpath):
            print(f"file {localpath} already exists")
            return None

    with requests.get(fileurl, stream=True) as rstream:
        rstream.raise_for_status()
        with open(localpath, 'wb') as fstream:
            for chunk in rstream.iter_content(chunk_size=8192):
                fstream.write(chunk)

    return localpath


def get_vote_data(province="ON", year=2021, overwrite=False):
    """
    Download vote result data from elections.ca

    Parameters
    ----------
    province : str
        two-letter abbreviation for the province
    year : int
        election year (one of 2008, 2011, 2015, 2019, 2021)
    overwrite : bool
        if False (default), do not overwrite existing file

    Returns
    -------
    str
        name of downloaded file
    """
    if year == 2008:
        base_url = ("https://www.elections.ca/"
                    + "scripts/OVR2008/31/data/")
    elif year == 2011:
        base_url = ("https://www.elections.ca/"
                    + "scripts/OVR2011/34/data_donnees/")
    elif year == 2015:
        base_url = ("https://www.elections.ca/"
                    + "res/rep/off/ovr2015app/41/data_donnees/")
    elif year == 2019:
        base_url = ("https://www.elections.ca/"
                    + "res/rep/off/ovr2019app/51/data_donnees/")
    elif year == 2021:
        base_url = ("https://www.elections.ca/"
                    + "res/rep/off/ovr2021app/53/data_donnees/")
    else:
        print(f"election year {year} not implemented")
        return

    filename = f"pollresults_resultatsbureau{provcodes[province]}.zip"

    fileurl = urljoin(base_url, filename)

    result = download_file(fileurl, prefix=f"{year}_", overwrite=overwrite)

    # generate riding name -> number map
    update_riding_map_file(province=province, year=year)

    return result


def get_all_vote_data(year=2021, overwrite=False):
    """
    Download vote data from all provinces and territories

    Parameters
    ----------
    year : int
        election year for which to download data
    overwrite : bool

    Returns
    -------
    str
        names of downloaded files (comma delimited)
    """
    result_list = []
    for province in provcodes:
        result = get_vote_data(province, year=year, overwrite=overwrite)
        if result is not None:
            result_list.append(result)
    return ",".join(result_list)


def get_geometries(year=2021, overwrite=False):
    """
    Download GIS shapefiles for electoral districts

    Parameters
    ----------
    year : int
        election year for which to download data
    overwrite : bool
        if False (default), do not overwrite existing file

    Returns
    -------
    tuple
        local filename(s) of download files
    """
    if year == 2008:
        base_url = ("https://ftp.geogratis.gc.ca/pub/nrcan_rncan/"
                    + "vector/electoral/2008/")
        filename = "pd308.2008.zip"
        # download shape files (no separate pdf documentation)
        shape_result = download_file(urljoin(base_url, filename),
                                     overwrite=overwrite)
        pdf_result = None
    elif year == 2011:
        base_url = ("https://ftp.geogratis.gc.ca/pub/nrcan_rncan/"
                    + "vector/electoral/2011/")
        filename = "pd308.2011.zip"
        # download shape files (no separate pdf documentation)
        shape_result = download_file(urljoin(base_url, filename),
                                     overwrite=overwrite)
        pdf_result = None
    elif year == 2015:
        base_url = ("https://ftp.maps.canada.ca/pub/elections_elections/"
                    + "Electoral-districts_Circonscription-electorale/"
                    + "polling_divisions_boundaries_2015/")
        pdf_base = base_url + "doc/"
        pdf_filename = "Data_Dictionary.pdf"
        filename = "polling_divisions_boundaries_2015_shp.zip"
        # download data dictionary file
        pdf_result = download_file(urljoin(pdf_base, pdf_filename),
                                   overwrite=overwrite)
        # download shape files
        shape_result = download_file(urljoin(base_url, filename),
                                     overwrite=overwrite)
    elif year == 2019:
        base_url = ("https://ftp.maps.canada.ca/pub/elections_elections/"
                    + "Electoral-districts_Circonscription-electorale/"
                    + "Elections_Canada_2019/")
        pdf_filename = "Elections_Canada_2019_Data_Dictionary.pdf"
        filename = "polling_divisions_boundaries_2019.shp.zip"
        # download data dictionary file
        pdf_result = download_file(urljoin(base_url, pdf_filename),
                                   overwrite=overwrite)
        # download shape files
        shape_result = download_file(urljoin(base_url, filename),
                                     overwrite=overwrite)
    elif year == 2021:
        base_url = ("https://ftp.maps.canada.ca/pub/elections_elections/"
                    + "Electoral-districts_Circonscription-electorale/"
                    + "Elections_Canada_2021/")
        pdf_filename = "Elections_Canada_2021_Data_Dictionary.pdf"
        filename = "PD_CA_2021_EN.zip"
        # download data dictionary file
        pdf_result = download_file(urljoin(base_url, pdf_filename),
                                   overwrite=overwrite)
        # download shape files
        shape_result = download_file(urljoin(base_url, filename),
                                     overwrite=overwrite)
    else:
        print(f"year {year} not implemented")
        return None

    return pdf_result, shape_result
