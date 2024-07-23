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
               "Argenteuil--La Petite-Nation"]
}
