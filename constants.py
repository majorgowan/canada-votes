"""
-------------------------------------------------------
Constants for canadavotes project
-------------------------------------------------------
Author:  Mark Fruman
Email:   mark.fruman@yahoo.com
-------------------------------------------------------
"""
import os

basedir = os.path.dirname(__file__)
datadir = os.path.join(basedir, "data")
datasetdir = os.path.join(basedir, "datasets")
outputdir = os.path.join(basedir, "output")

geometry_files = {
    2008: {"filename": "pd308.2008.zip",
           "layer": "pd308_a"},
    2011: {"filename": "pd308.2011.zip",
           "layer": "pd_a"},
    2015: {"filename": "polling_divisions_boundaries_2015_shp.zip",
           "layer": None},
    2019: {"filename": "polling_divisions_boundaries_2019.shp.zip",
           "layer": None},
    2021: {"filename": "PD_CA_2021_EN.zip",
           "layer": None}
}

votes_encodings = {
    2008: "latin-1",
    2011: "latin-1",
    2015: "utf-8",
    2019: "utf-8",
    2021: "utf_8"
}

provcodes = {
    "AB": 48,
    "BC": 59,
    "MB": 46,
    "NB": 13,
    "NL": 10,
    "NS": 12,
    "NT": 61,
    "NU": 62,
    "ON": 35,
    "PE": 11,
    "QC": 24,
    "SK": 47,
    "YT": 60
}

codeprovs = {v: k for k, v in provcodes.items()}

partycolours = {
    "Conservative": "darkblue",
    "Liberal": "red",
    "Bloc Québécois": "lightblue",
    "NDP-New Democratic Party": "orange",
    "Green Party": "green",
    "People's Party - PPC": "purple",
    "People's Party": "purple",
    "Communist": "pink"
}

areas = {
    "brampton": [
        "Brampton Centre",
        "Brampton East",
        "Brampton North",
        "Brampton South",
        "Brampton West"
    ],
    "calgary": [
        "Calgary Centre",
        "Calgary Centre-North",
        "Calgary Confederation",
        "Calgary East",
        "Calgary Forest Lawn",
        "Calgary Heritage",
        "Calgary Midnapore",
        "Calgary Northeast",
        "Calgary Nose Hill",
        "Calgary Rocky Ridge",
        "Calgary Shepard",
        "Calgary Signal Hill",
        "Calgary Skyview",
        "Calgary Southeast",
        "Calgary Southwest",
        "Calgary West",
        "Calgary--Nose Hill"
    ],
    "cottage_country": [
        "Barrie",
        "Barrie--Innisfil",
        "Barrie--Springwater--Oro-Medonte",
        "Parry Sound--Muskoka",
        "Simcoe North",
        "Simcoe--Grey",
        "York--Simcoe"
    ],
    "downtown_toronto": [
        "Davenport",
        "Spadina--Fort York",
        "Toronto Centre",
        "Toronto--Danforth",
        "Toronto--St. Paul's",
        "University--Rosedale"
    ],
    "etobicoke": [
        "Etobicoke Centre",
        "Etobicoke North",
        "Etobicoke--Lakeshore",
        "Humber River--Black Creek",
        "Parkdale--High Park",
        "York South--Weston"
    ],
    "hamilton": [
        "Flamborough--Glanbrook",
        "Hamilton Centre",
        "Hamilton East--Stoney Creek",
        "Hamilton Mountain",
        "Hamilton West--Ancaster--Dundas"
    ],
    "kitchener_waterloo": [
        "Kitchener Centre",
        "Kitchener South--Hespeler",
        "Kitchener--Conestoga",
        "Waterloo"
    ],
    "london": [
        "Elgin--Middlesex--London",
        "Lambton--Kent--Middlesex",
        "London North Centre",
        "London West",
        "London--Fanshawe",
        "Oxford",
        "Perth--Wellington",
        "Sarnia--Lambton"
    ],
    "milton": [
        "Burlington",
        "Guelph",
        "Halton",
        "Milton",
        "Oakville",
        "Oakville North--Burlington",
        "Wellington--Halton Hills"
    ],
    "mississauga": [
        "Mississauga Centre",
        "Mississauga East--Cooksville",
        "Mississauga--Erin Mills",
        "Mississauga--Lakeshore",
        "Mississauga--Malton",
        "Mississauga--Streetsville"
    ],
    "montreal": [
        "Ahuntsic-Cartierville",
        "Alfred-Pellan",
        "Bourassa",
        "Dorval--Lachine--LaSalle",
        "Hochelaga",
        "Honoré-Mercier",
        "La Pointe-de-l'Île",
        "Lac-Saint-Louis",
        "Laurier--Sainte-Marie",
        "Laval--Les Îles",
        "Marc-Aurèle-Fortin",
        "Mount Royal",
        "Notre-Dame-de-Grâce--Westmount",
        "Outremont",
        "Papineau",
        "Pierrefonds--Dollard",
        "Rosemont--La Petite-Patrie",
        "Saint-Laurent",
        "Saint-Léonard--Saint-Michel",
        "Vimy"
    ],
    "north_toronto": [
        "Don Valley East",
        "Don Valley North",
        "Don Valley West",
        "Eglinton--Lawrence",
        "Willowdale",
        "York Centre"
    ],
    "ottawa": [
        "Argenteuil--La Petite-Nation",
        "Carleton",
        "Gatineau",
        "Glengarry--Prescott--Russell",
        "Hull--Aylmer",
        "Kanata--Carleton",
        "Nepean",
        "Orléans",
        "Ottawa Centre",
        "Ottawa South",
        "Ottawa West--Nepean",
        "Ottawa--Vanier",
        "Pontiac"
    ],
    "pei": [
        "Cardigan",
        "Charlottetown",
        "Egmont",
        "Malpeque"
    ],
    "quebec": [
        "Beauce",
        "Beauport--Limoilou",
        "Beauport-Côte-de-Beaupré-Île d'Orléans-Charlevoix",
        "Bellechasse--Les Etchemins--Lévis",
        "Charlesbourg--Haute-Saint-Charles",
        "Louis-Hébert",
        "Louis-Saint-Laurent",
        "Lévis--Lotbinière",
        "Portneuf--Jacques-Cartier",
        "Québec"
    ],
    "scarborough": [
        "Scarborough Centre",
        "Scarborough North",
        "Scarborough Southwest",
        "Scarborough--Agincourt",
        "Scarborough--Guildwood",
        "Scarborough--Rouge Park"
    ],
    "surrey": [
        "Cloverdale--Langley City",
        "Fleetwood--Port Kells",
        "Newton--North Delta",
        "Port Moody--Coquitlam",
        "South Surrey--White Rock",
        "South Surrey--White Rock--Cloverdale",
        "Surrey Centre",
        "Surrey North",
        "Surrey--Newton"
    ],
    "vancouver": [
        "Burnaby South",
        "Burnaby--Douglas",
        "Burnaby--New Westminster",
        "New Westminster--Burnaby",
        "New Westminster--Coquitlam",
        "Vancouver Centre",
        "Vancouver East",
        "Vancouver Granville",
        "Vancouver Kingsway",
        "Vancouver Quadra",
        "Vancouver South"
    ],
    "vaughan": [
        "Aurora--Oak Ridges--Richmond Hill",
        "King--Vaughan",
        "Markham--Stouffville",
        "Markham--Thornhill",
        "Markham--Unionville",
        "Newmarket--Aurora",
        "Oak Ridges--Markham",
        "Richmond Hill",
        "Thornhill",
        "Vaughan",
        "Vaughan--Woodbridge"
    ],
    "victoria": [
        "Cowichan--Malahat--Langford",
        "Esquimalt--Juan de Fuca",
        "Esquimalt--Saanich--Sooke",
        "Nanaimo--Cowichan",
        "Saanich--Gulf Islands",
        "Victoria"
    ],
    "winnipeg": [
        "Charleswood--St. James--Assiniboia",
        "Charleswood--St. James--Assiniboia--Headingley",
        "Elmwood--Transcona",
        "Kildonan--St. Paul",
        "Saint Boniface",
        "Saint Boniface--Saint Vital",
        "Winnipeg Centre",
        "Winnipeg North",
        "Winnipeg South",
        "Winnipeg South Centre"
    ]
}

datasets = {
    "hortons": {
        "filename": "TimHortons_locations.csv"
    },
    "bubble_tea": {
        "filename": "bubble_tea.csv"
    },
    "worship": {
        "url": ("https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/"
                + "8e22e693-3394-4dfa-8dc0-eb436db38603/resource/"
                + "7e36ad86-496c-45a1-87cb-6e7592aa2adc/download/"
                + "places-of-worship-data-wgs84.zip"),
        "filename": "places-of-worship-data-wgs84.zip"
    },
    "dinesafe": {
        "url": ("https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/"
                + "b6b4f3fb-2e2c-47e7-931d-b87d22806948/resource/"
                + "eda39233-4791-464e-98e6-094f51a01916/download/"
                + "Dinesafe.csv"),
        "filename": "Dinesafe.csv"
    },
    "sortation": {
        "url": ("https://www12.statcan.gc.ca/census-recensement/2011/"
                + "geo/bound-limit/files-fichiers/2016/lfsa000b16a_e.zip"),
        "filename": "sortation_areas.zip"
    }
}