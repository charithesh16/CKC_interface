import folium.map
import pandas as pd
import folium
from flask import Flask,render_template_string, jsonify, redirect, url_for, send_file
import plotly.express as px
import re
import geopandas as gpd
from shapely.geometry import Point
from folium.plugins import MarkerCluster
from wordcloud import WordCloud
import io
import base64
import json
import os
from datetime import datetime

from app import parsed_data

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import json
from datetime import datetime
import re
from collections import defaultdict
import numpy as np
from concurrent.futures import ThreadPoolExecutor

# Constants
EXCLUDE_KEYS = {"coordinates", "keywords", "articles", "locations", "row_count",
                "keyword_count", "emptyLocations", "emptyKeywords"}
exclude_keys = set(["coordinates","keywords","articles","locations","row_count","keyword_count","emptyLocations","emptyKeywords"])

def read_dataset():
    # Use more efficient pandas operations
    dataset = pd.read_excel('./data/merged/merged_output.xlsx')
    mask = dataset['keywords'].notna() | dataset['Exact Match Locations'].notna()
    dataset = dataset[mask]
    dataset = dataset[dataset['keywords'].str.len() > 0 |
                     dataset['Exact Match Locations'].str.len() > 0]
    return dataset
def read_shape_files():
    # Load shapefiles with caching
    base_path = './Vietnam_Shapefile/gadm41_VNM_shp/'
    files = {
        'cities': 'gadm41_VNM_3.shp',
        'district': 'gadm41_VNM_2.shp',
        'province': 'gadm41_VNM_1.shp',
        'country': 'gadm41_VNM_0.shp'
    }
    gdfs = {k: gpd.read_file(f"{base_path}{v}") for k, v in files.items()}
    return (gdfs['province'], gdfs['district'], gdfs['cities'], gdfs['country'])

def extract_coordinates(x):
    # Faster coordinate extraction without regex
    if not isinstance(x, str):
        return []
    coords = []
    parts = x.split('(')
    for p in parts[1:]:
        name = parts[0].strip()
        coords_part = p.split(')')[0]
        lat, lon = map(float, coords_part.split(','))
        coords.append((name, lat, lon))
    return coords
def rowToDict(row):
    # Use dict comprehension for better performance
    fields = ['date/year', 'source', 'sentence', 'context', 'NER Locations',
              'Companies', 'keywords', 'subject', 'byline', 'title',
              'Exact Match Locations', 'AD1', 'AD2', 'AD3']
    return {k.lower().replace('/', '_'): row.get(k, '') or '' for k in fields}

def create_template():
    return {
        'coordinates': None,
        'row_count': 0,
        'keyword_count': 0,
        'keywords': defaultdict(int),
        'articles': [],
        'locations': defaultdict(list)
    }


def populate_data(parsed_data, cities_gdf, dataset):
    # Create spatial index for faster lookups
    spatial_index = cities_gdf.sindex

    # Process coordinates in parallel
    dataset['coordinates'] = dataset['Exact Match Locations'].apply(extract_coordinates)

    def process_row(row):
        if not row['coordinates'] and pd.notna(row['keywords']) and row['keywords'].split(', '):
            return ('empty', row)

        results = []
        for name, lat, lon in row['coordinates']:
            point = Point(float(lon), float(lat))
            possible_matches_index = list(spatial_index.intersection(point.bounds))
            possible_matches = cities_gdf.iloc[possible_matches_index]

            for _, city in possible_matches.iterrows():
                if city['geometry'].contains(point):
                    results.append((city, name, lat, lon, row))
                    break
        return results

    # Process rows in parallel
    with ThreadPoolExecutor() as executor:
        for batch in np.array_split(dataset.iterrows(), 10):
            futures = [executor.submit(process_row, row[1]) for row in batch]
            for future in futures:
                results = future.result()
                if results == 'empty':
                    parsed_data["Vietnam"]["emptyLocations"].append(rowToDict(results[1]))
                else:
                    for city, name, lat, lon, row in results:
                        update_city_data(parsed_data, city, name, lat, lon, row)

    return parsed_data


def update_city_data(parsed_data, city, name, lat, lon, row):
    city_data = parsed_data[city["COUNTRY"]][city["NAME_1"]][city["NAME_2"]][city["NAME_3"]]
    city_data["row_count"] += 1
    city_data["locations"][name] = [lat, lon]

    if pd.notna(row['keywords']):
        minerals = row['keywords'].split(', ')
        city_data['keyword_count'] += len(minerals)
        for mineral in minerals:
            city_data['keywords'][mineral] += 1

    if pd.notna(row['source']):
        city_data['articles'].append(rowToDict(row))


def province_placeholder(parsed_data, province_gdf):
    for _,province in province_gdf.iterrows():
        parsed_data[province["COUNTRY"]][province["NAME_1"]] = {
            'coordinates': province['geometry'].centroid.coords[0][::-1],
            'row_count': 0,
            'keyword_count': 0,
            'keywords': {},
            'articles': [],
            'locations': {}
        }
    return parsed_data
def district_placeholder(parsed_data, district_gdf):
    for _,district in district_gdf.iterrows():
        parsed_data[district["COUNTRY"]][district["NAME_1"]][district["NAME_2"]] = {
            'coordinates': district['geometry'].centroid.coords[0][::-1],
            'row_count': 0,
            'keyword_count': 0,
            'keywords': {},
            'articles': [],
            'locations': {}
        }
    return parsed_data
def cities_placeholder(parsed_data, cities_gdf):
    for _,city in cities_gdf.iterrows():
        parsed_data[city["COUNTRY"]][city["NAME_1"]][city["NAME_2"]][city["NAME_3"]] = {
            'coordinates': city['geometry'].centroid.coords[0][::-1],
            'row_count': 0,
            'keyword_count': 0,
            'keywords': {},
            'articles': [],
            'locations': {}
        }
    return parsed_data

def country_placeholder(parsed_data):
    parsed_data["Vietnam"] = {
        'coordinates': [14.0583, 108.2772],
        'row_count': 0,
        'keyword_count': 0,
        'keywords': {},
        'articles': [],
        'locations': {},
        'emptyLocations':[],
        'emptyKeywords':[]
    }
    return parsed_data

def get_district_data(country,province,district,parsed_data):
    # global parsed_data
    row_count = 0
    keyword_count = 0
    keywords={}
    articles = []
    global exclude_keys
    for city in parsed_data[country][province][district].keys():
        if city not in exclude_keys:
            city_data = parsed_data[country][province][district][city]
            row_count += city_data["row_count"]
            keyword_count += city_data["keyword_count"]
            for keyword,count in city_data["keywords"].items():
                if keyword not in keywords:
                    keywords[keyword] = 0
                keywords[keyword] += count
            articles.extend(city_data["articles"])
    parsed_data[country][province][district]["row_count"] = row_count
    parsed_data[country][province][district]["keyword_count"] = keyword_count
    parsed_data[country][province][district]["articles"] = articles
    parsed_data[country][province][district]["keywords"] = keywords
    return row_count,keyword_count,articles,keywords

def get_province_data(country,province,parsed_data):
    # global parsed_data
    row_count = 0
    keyword_count = 0
    keywords = {}
    articles = []
    global exclude_keys
    for district in parsed_data[country][province].keys():
        if district not in exclude_keys:
            rc,kc,ar,kw=get_district_data(country,province,district,parsed_data)
            row_count += rc
            keyword_count += kc
            for k,count in kw.items():
                if k not in keywords:
                    keywords[k] = 0
                keywords[k] += count
            articles.extend(ar)
    parsed_data[country][province]["row_count"] = row_count
    parsed_data[country][province]["keyword_count"] = keyword_count
    parsed_data[country][province]["articles"] = articles
    parsed_data[country][province]["keywords"] = keywords
    return row_count,keyword_count,articles,keywords

def get_country_details(country_name,parsed_data):
    # global parsed_data
    row_count = 0
    keyword_count = 0
    keywords = {}
    articles = []
    global exclude_keys
    for province in parsed_data[country_name].keys():
        if province not in exclude_keys:
            rc,kc,ar,kw=get_province_data(country_name,province,parsed_data)
            row_count += rc
            keyword_count += kc
            for k, count in kw.items():
                if k not in keywords:
                    keywords[k] = 0
                keywords[k] += count
            articles.extend(ar)
    parsed_data[country_name]["row_count"] = row_count
    parsed_data[country_name]["keyword_count"] = keyword_count
    parsed_data[country_name]["articles"] = articles
    parsed_data[country_name]["keywords"] = keywords
    return row_count,keyword_count,articles,keywords

def filter_data(original_data,search_term,columns,start_date,end_date):
    filtered_data = dict()
    province_gdf, district_gdf, cities_gdf, country_gdf = read_shape_files()
    filtered_data = country_placeholder(filtered_data)
    filtered_data = province_placeholder(filtered_data, province_gdf)
    filtered_data = district_placeholder(filtered_data, district_gdf)
    filtered_data = cities_placeholder(filtered_data, cities_gdf)
    global exclude_keys
    for country in [key for key in original_data.keys() if key not in exclude_keys]:
        for province in [key for key in original_data[country].keys() if key not in exclude_keys]:
            # print(province)
            for district in [key for key in original_data[country][province].keys() if key not in exclude_keys]:
                # print(district)
                for city in [key for key in original_data[country][province][district].keys() if key not in exclude_keys]:
                    city_data = original_data[country][province][district][city].copy()
                    filtered_articles = []
                    filtered_row_count = 0
                    filtered_keyword_count = 0
                    filtered_keywords = dict()

                    for values in city_data['articles']:
                        source_url = values["source"]
                        if in_date_range(start_date,end_date,values["date"]) and has_term(columns,search_term,values):
                            filtered_articles.append(values)
                            filtered_row_count+=1
                            minerals = values["keywords"].split(", ")
                            filtered_keyword_count += len(minerals)
                            for mineral in minerals:
                                mineral = mineral.lower().strip()
                                filtered_keywords[mineral] = filtered_keywords.get(mineral,0)+1
                    city_data["articles"] = filtered_articles
                    city_data["keyword_count"] = filtered_keyword_count
                    city_data["keywords"] = filtered_keywords
                    city_data["row_count"] = filtered_row_count
                    filtered_data[country][province][district][city] = city_data
    get_country_details("Vietnam", filtered_data)
    return filtered_data


from datetime import datetime
import re


def in_date_range(start_date, end_date, date_str):
    # Null checks
    if start_date is None or end_date is None or date_str is None:
        return True
    target_date = datetime.strptime(date_str, "%m/%d/%Y")
    return start_date <= target_date <= end_date

def has_term(columns, search_term, values):
    # Null checks
    if columns is None or search_term is None or values is None:
        return True
    for column in columns:
        # Check if the column exists in values and that the value is not None
        if column in values and values[column] is not None:
            pattern = rf'\b{re.escape(search_term)}\b'
            if bool(re.search(pattern, values[column])):
                return True
    return False


def generate_data():
    dataset = read_dataset()
    province_gdf, district_gdf, cities_gdf, country_gdf = read_shape_files()

    # Initialize data structure with defaultdict
    parsed_data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(create_template))))

    # Set up placeholders
    for gdf_name, gdf in [('country', country_gdf), ('province', province_gdf),
                          ('district', district_gdf), ('cities', cities_gdf)]:
        for _, region in gdf.iterrows():
            template = create_template()
            template['coordinates'] = region['geometry'].centroid.coords[0][::-1]
            if gdf_name == 'country':
                parsed_data[region["COUNTRY"]] = template
            elif gdf_name == 'province':
                parsed_data[region["COUNTRY"]][region["NAME_1"]] = template
            elif gdf_name == 'district':
                parsed_data[region["COUNTRY"]][region["NAME_1"]][region["NAME_2"]] = template
            else:
                parsed_data[region["COUNTRY"]][region["NAME_1"]][region["NAME_2"]][region["NAME_3"]] = template

    # Populate and save data
    parsed_data = populate_data(parsed_data, cities_gdf, dataset)

    # Save intermediate data
    with open("data/keyword_or_loc_data_intermediate.json", 'w') as f:
        json.dump(parsed_data, f)

    get_country_details("Vietnam", parsed_data)

    # Save final data
    with open("data/keyword_or_loc_data.json", 'w') as f:
        json.dump(parsed_data, f)

    return "Successfully saved cities data"