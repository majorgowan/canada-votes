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
outputdir = os.path.join(basedir, "output")

geometry_files = {
    2008: {"filename": "pd308.2008.zip",
           "layer": "pd308_a"},
    2011: {"filename": "pd308.2011.zip",
           "layer": "pd_a"},
    2015: {"filename": "polling_divisions_boundaries_2015_shp.zip",
           "layer": None},
    2019: {"filename": "polling_divisions_boundaries_2019_shp.zip",
           "layer": None},
    2021: {"filename": "PD_CA_2021_EN.zip",
           "layer": None}
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
    "People's Party - PPC": "purple"
}

areas = {
    "downtown_toronto": ["Toronto Centre",
                         "University--Rosedale",
                         "Spadina--Fort York",
                         "Davenport",
                         "Toronto--St. Paul's",
                         "Toronto--Danforth"],
    "north_toronto": ["York Centre",
                      "Willowdale",
                      "Don Valley West",
                      "Don Valley East",
                      "Don Valley North",
                      "Eglinton--Lawrence"],
    "scarborough": ["Scarborough Centre",
                    "Scarborough North",
                    "Scarborough Southwest",
                    "Scarborough--Agincourt",
                    "Scarborough--Guildwood",
                    "Scarborough--Rouge Park"],
    "etobicoke": ["Etobicoke Centre",
                  "Etobicoke North",
                  "Etobicoke--Lakeshore",
                  "Humber River--Black Creek",
                  "Parkdale--High Park",
                  "York South--Weston"],
    "mississauga": ["Mississauga Centre",
                    "Mississauga East--Cooksville",
                    "Mississauga--Erin Mills",
                    "Mississauga--Lakeshore",
                    "Mississauga--Malton",
                    "Mississauga--Streetsville"],
    "vaughan": ["Aurora--Oak Ridges--Richmond Hill",
                "King--Vaughan",
                "Markham--Stouffville",
                "Markham--Thornhill",
                "Markham--Unionville",
                "Richmond Hill",
                "Vaughan--Woodbridge",
                "Thornhill",
                "Newmarket--Aurora"],
    "brampton": ["Brampton Centre",
                 "Brampton East",
                 "Brampton North",
                 "Brampton South",
                 "Brampton West"],
    "milton": ["Milton",
               "Burlington",
               "Wellington--Halton Hills",
               "Guelph"],
    "hamilton": ["Hamilton Centre",
                 "Hamilton East--Stoney Creek",
                 "Hamilton Mountain",
                 "Hamilton West--Ancaster--Dundas",
                 "Flamborough--Glanbrook"],
    "cottage_country": ["Barrie--Innisfil",
                        "Barrie--Springwater--Oro-Medonte",
                        "Parry Sound--Muskoka",
                        "Simcoe North",
                        "Simcoe--Grey",
                        "York--Simcoe"],
    "london": ["London North Centre",
               "London West",
               "London--Fanshawe"],
    "kitchener_waterloo": ["Kitchener Centre",
                           "Kitchener South--Hespeler",
                           "Kitchener--Conestoga",
                           "Waterloo"],
    "ottawa": ["Carleton",
               "Kanata--Carleton",
               "Nepean",
               "Ottawa Centre",
               "Ottawa South",
               "Ottawa West--Nepean",
               "Ottawa--Vanier",
               "Orléans",
               "Glengarry--Prescott--Russell",
               "Gatineau",
               "Hull--Aylmer",
               "Pontiac",
               "Argenteuil--La Petite-Nation"],
    "calgary": ["Calgary Centre",
                "Calgary Centre-North",
                "Calgary Confederation",
                "Calgary East",
                "Calgary Forest Lawn",
                "Calgary Heritage",
                "Calgary Midnapore",
                "Calgary Northeast",
                "Calgary Nose Hill",
                "Calgary--Nose Hill",
                "Calgary Rocky Ridge",
                "Calgary Shepard",
                "Calgary Signal Hill",
                "Calgary Skyview",
                "Calgary Southeast",
                "Calgary Southwest",
                "Calgary West"],
    "winnipeg": ["Winnipeg Centre",
                 "Winnipeg North",
                 "Winnipeg South",
                 "Winnipeg South Centre",
                 "Kildonan--St. Paul",
                 "Elmwood--Transcona",
                 "Charleswood--St. James--Assiniboia",
                 "Charleswood--St. James--Assiniboia--Headingley",
                 "Saint Boniface",
                 "Saint Boniface--Saint Vital"],
    "montreal": ["Papineau",
                 "Rosemont--La Petite-Patrie",
                 "Outremont",
                 "Saint-Léonard--Saint-Michel",
                 "Laurier--Sainte-Marie",
                 "Ahuntsic-Cartierville",
                 "Bourassa",
                 "Hochelaga",
                 "Mount Royal",
                 "Notre-Dame-de-Grâce--Westmount",
                 "Vimy",
                 "Saint-Laurent",
                 "Honoré-Mercier",
                 "Alfred-Pellan",
                 "La Pointe-de-l'Île",
                 "Dorval--Lachine--LaSalle",
                 "Marc-Aurèle-Fortin",
                 "Laval--Les Îles",
                 "Pierrefonds--Dollard",
                 "Lac-Saint-Louis"],
    "quebec": ["Québec",
               "Beauport--Limoilou",
               "Louis-Hébert",
               "Louis-Saint-Laurent",
               "Charlesbourg--Haute-Saint-Charles",
               "Lévis--Lotbinière",
               "Bellechasse--Les Etchemins--Lévis",
               "Portneuf--Jacques-Cartier",
               "Beauce",
               "Beauport-Côte-de-Beaupré-Île d'Orléans-Charlevoix"],
    "pei": ["Charlottetown",
            "Malpeque",
            "Cardigan",
            "Egmont"]
}
