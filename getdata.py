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


def download_file(fileurl, overwrite=False):
    """
    Download a file in chunks

    Parameters
    ----------
    fileurl : str
        address of file to download
    overwrite : bool
        if False (default), do not overwrite existing file

    Returns
    -------
    str
        local filename
    """
    filename = fileurl.split("/")[-1]
    localpath = os.path.join(datadir, filename)

    if not overwrite:
        if os.path.exists(localpath):
            print(f"file {filename} already exists")
            return None

    with requests.get(fileurl, stream=True) as rstream:
        rstream.raise_for_status()
        with open(localpath, 'wb') as fstream:
            for chunk in rstream.iter_content(chunk_size=8192):
                fstream.write(chunk)

    return localpath


def get_vote_data(province="ON", overwrite=False):
    """
    Download vote result data from elections.ca

    Parameters
    ----------
    province : str
        two-letter abbreviation for the province
    overwrite : bool
        if False (default), do not overwrite existing file

    Returns
    -------
    str
        name of downloaded file
    """
    base_url = "https://elections.ca/res/rep/off/ovr2021app/53/data_donnees/"
    filename = f"pollresults_resultatsbureau{provcodes[province]}.zip"

    fileurl = urljoin(base_url, filename)

    result = download_file(fileurl, overwrite)

    # generate riding name -> number map
    update_riding_map_file(province)

    return result


def get_all_vote_data(overwrite=False):
    """
    Download vote data from all provinces and territories

    Parameters
    ----------
    overwrite : bool

    Returns
    -------
    str
        names of downloaded files (comma delimited)
    """
    result_list = []
    for province in provcodes:
        result = get_vote_data(province, overwrite=overwrite)
        if result is not None:
            result_list.append(result)
    return ",".join(result_list)


def get_geometries(advance=False, overwrite=False):
    """
    Download GIS shapefiles for electoral districts

    Parameters
    ----------
    advance : bool
        if True, download shape files for advance poll zone boundaries;
        otherwise download shape files for election-day poll zones
    overwrite : bool
        if False (default), do not overwrite existing file

    Returns
    -------
    tuple
        local filename(s) of download files
    """
    base_url = ("https://ftp.maps.canada.ca/pub/elections_elections/"
                 + "Electoral-districts_Circonscription-electorale/"
                 + "Elections_Canada_2021/")
    pdf_filename = "Elections_Canada_2021_Data_Dictionary.pdf"
    if advance:
        filename = "ADVPD_CA_2021_EN.zip"
    else:
        filename = "PD_CA_2021_EN.zip"

    # download data dictionary file
    pdf_result = download_file(urljoin(base_url, pdf_filename), overwrite)
    # download shape files
    shape_result = download_file(urljoin(base_url, filename), overwrite)

    return pdf_result, shape_result
