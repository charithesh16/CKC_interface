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
exclude_keys = set(["coordinates","keywords","articles","locations","row_count","keyword_count","emptyLocations","emptyKeywords"])

def read_dataset():
    dataset = pd.read_excel('./data/merged/merged_output.xlsx')
    dataset = dataset[(dataset['keywords'].str.strip() != '') | (dataset['Exact Match Locations'].str.strip() != '')]
    dataset = dataset.dropna(subset=['keywords', 'Exact Match Locations'],how="all")
    # have a list of locations in the form (name,lat,lon)
    return dataset
def read_shape_files():
    cities_gdf = gpd.read_file('./Vietnam_Shapefile/gadm41_VNM_shp/gadm41_VNM_3.shp')
    district_gdf = gpd.read_file('./Vietnam_Shapefile/gadm41_VNM_shp/gadm41_VNM_2.shp')
    province_gdf = gpd.read_file('./Vietnam_Shapefile/gadm41_VNM_shp/gadm41_VNM_1.shp')
    country_gdf = gpd.read_file('./Vietnam_Shapefile/gadm41_VNM_shp/gadm41_VNM_0.shp')
    return province_gdf,district_gdf,cities_gdf,country_gdf

# def rowToDict(row):
#     return {
#         "date": row.get('date/year', '') or '',
#         "source": row.get("source", '') or '',
#         "sentence": row.get("sentence", '') or '',
#         "context": row.get("context", '') or '',
#         "ner_locations": row.get("NER Locations", '') or '',
#         "companies": row.get("Companies", '') or '',
#         "keywords": row.get("keywords", '') or '',
#         "subject": row.get("subject", '') or '',
#         "byline": row.get("byline", '') or '',
#         "title": row.get("title", '') or '',
#         "exact match locations": row.get("Exact Match Locations", '') or '',
#         "ad1": row.get("AD1", '') or '',
#         "ad2": row.get("AD2", '') or '',
#         "ad3": row.get("AD3", '') or ''
#     }


import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import numpy as np
from typing import Dict, Any
import re
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from functools import partial
import warnings

warnings.filterwarnings('ignore')


def process_coordinates(x: str) -> list:
    return re.findall(r'(\w+(?:\s+\w+)*)\s*\((\d+\.\d+),\s*(\d+\.\d+)\)', str(x) if isinstance(x, str) else '')


def rowToDict(row: pd.Series) -> dict:
    """Optimized row to dictionary conversion."""
    fields = ['date', 'source', 'sentence', 'context', 'NER Locations',
              'Companies', 'keywords', 'subject', 'byline', 'title',
              'Exact Match Locations', 'AD1', 'AD2', 'AD3']

    return {field.lower().replace('/', '_'): row.get(field, '') or ''
            for field in fields}


def process_chunk(chunk_data: tuple) -> list:
    """Process a chunk of data in parallel."""
    chunk, cities_spatial_index, cities_data = chunk_data
    results = []

    for _, row in chunk.iterrows():
        # row_results = []

        # Skip if no valid coordinates but has keywords
        #     if (pd.isna(row['coordinates']) or len(row['coordinates']) == 0 ) and (pd.notna(row['keywords']) and len(row['keywords'].split(', ')) > 0):
        if len(row['coordinates']) <=0 and (pd.notna(row['keywords']) and len(row['keywords'].split(',')) > 0):
            results.append(('empty', rowToDict(row)))
            # results.extend(row_results)
            continue
        # Process coordinates
        for name, lat, lon in row['coordinates']:
            point = Point(float(lon), float(lat))
            possible_matches = list(cities_spatial_index.intersection(point.bounds))

            for idx in possible_matches:
                city = cities_data[idx]
                if city['geometry'].contains(point):
                    result = {
                        'city_info': {
                            'country': city['COUNTRY'],
                            'name_1': city['NAME_1'],
                            'name_2': city['NAME_2'],
                            'name_3': city['NAME_3']
                        },
                        'location': {'name': name, 'coords': [lat, lon]},
                        'keywords': row['keywords'] if pd.notna(row['keywords']) else None,
                        'row_dict': rowToDict(row) if pd.notna(row['source']) else None
                    }
                    results.append(('data', result))
                    break

        # results.extend(row_results)
    return results


def populate_data(parsed_data: Dict[str, Any], cities_gdf: gpd.GeoDataFrame,
                  dataset: pd.DataFrame) -> Dict[str, Any]:
    """Optimized data population using parallel processing."""

    # Create spatial index
    if not cities_gdf.sindex:
        cities_gdf = cities_gdf.copy()
        cities_gdf.sindex

    # Pre-process coordinates
    print("Processing coordinates...")
    dataset['coordinates'] = dataset['Exact Match Locations'].apply(process_coordinates)

    # Prepare cities data for parallel processing
    cities_data = cities_gdf.to_dict('records')
    cities_spatial_index = cities_gdf.sindex

    # Split data into chunks
    chunk_size = 10000  # Adjust based on available memory
    chunks = [dataset[i:i + chunk_size] for i in range(0, len(dataset), chunk_size)]

    # Prepare chunk data for parallel processing
    chunk_data = [(chunk, cities_spatial_index, cities_data) for chunk in chunks]

    # Process chunks in parallel
    print("Processing chunks in parallel...")
    num_processes = multiprocessing.cpu_count() - 1
    with ProcessPoolExecutor(max_workers=num_processes) as executor:
        all_results = list(executor.map(process_chunk, chunk_data))

    # Aggregate results
    print("Aggregating results...")
    empty_location_count = 0
    for chunk_results in all_results:
        for result_type, result in chunk_results:
            if result_type == 'empty':
                parsed_data["Vietnam"]["emptyLocations"].append(result)
                empty_location_count += 1
            else:
                city_info = result['city_info']
                city_data = parsed_data[city_info['country']][city_info['name_1']] \
                    [city_info['name_2']][city_info['name_3']]

                # Update counts and locations
                city_data["row_count"] += 1
                city_data["locations"][result['location']['name']] = result['location']['coords']

                # Process keywords
                if result['keywords']:
                    minerals = result['keywords'].split(', ')
                    city_data['keyword_count'] += len(minerals)
                    for mineral in minerals:
                        city_data['keywords'][mineral] = \
                            city_data['keywords'].get(mineral, 0) + 1

                # Add article
                if result['row_dict']:
                    city_data['articles'].append(result['row_dict'])
                parsed_data[city_info['country']][city_info['name_1']][city_info['name_2']][city_info['name_3']] = city_data

    print(f"Empty location count: {empty_location_count}")
    return parsed_data


# def populate_data(parsed_data,cities_gdf,dataset):
#     '''data[country][province][district][city]= {
#     'row_count':<count>,
#     'keyword_count':<count>,
#     'keywords':{'keyword1':'keyword1','keyword2':'keyword2'
#     },
#     'locations':{'location1':[coords1,coords2]}
#     '''
#     dataset['coordinates'] = dataset['Exact Match Locations'].apply(
#         lambda x: re.findall(r'(\w+(?:\s+\w+)*)\s*\((\d+\.\d+),\s*(\d+\.\d+)\)', str(x) if isinstance(x, str) else '')
#     )
#     rows_processed=0
#     count = 0
#     for _,row in dataset.iterrows():
#         if (len(row['coordinates'])==0 and pd.notna(row['keywords'])) and len(row['keywords'].split(', '))>0:
#             count+=1
#             if count%500==0:
#                 print("empty location ",count)
#             parsed_data["Vietnam"]["emptyLocations"].append(rowToDict(row))
#             continue
#         for name,lat,lon in row['coordinates']:
#             point = Point(float(lon), float(lat))
#             for _,city in cities_gdf.iterrows():
#                 if city['geometry'].contains(point):
#                     parsed_data[city["COUNTRY"]][city["NAME_1"]][city["NAME_2"]][city["NAME_3"]]["row_count"]+=1
#                     parsed_data[city["COUNTRY"]][city["NAME_1"]][city["NAME_2"]][city["NAME_3"]]["locations"][name] =[lat,lon]
#                     if pd.notna(row['keywords']):
#                         minerals = row['keywords'].split(', ')
#                         parsed_data[city["COUNTRY"]][city["NAME_1"]][city["NAME_2"]][city["NAME_3"]]['keyword_count'] += len(minerals)
#                         for mineral in minerals:
#                             parsed_data[city["COUNTRY"]][city["NAME_1"]][city["NAME_2"]][city["NAME_3"]]['keywords'][mineral] = parsed_data[city["COUNTRY"]][city["NAME_1"]][city["NAME_2"]][city["NAME_3"]]['keywords'].get(mineral, 0) + 1
#                     if pd.notna(row['source']):
#                         (parsed_data[city["COUNTRY"]][city["NAME_1"]][city["NAME_2"]][city["NAME_3"]]['articles']
#                          .append(rowToDict(row)))
#                     break  # Assuming a point belongs to only one region
#         rows_processed+=1
#         if rows_processed%500==0:
#             print("processed ",rows_processed)
#     print("empty location count",count)
#     return parsed_data


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
    filtered_data["Vietnam"]["emptyLocations"] = original_data["Vietnam"]["emptyLocations"]
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
                            if pd.notna(values["keywords"]):
                                minerals = str(values["keywords"]).split(", ")
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
            if bool(re.search(pattern, str(values[column]))):
                return True
    return False

def generate_data():
    # Read data
    print("reading data")
    dataset = read_dataset()
    print("reading shape files")
    province_gdf, district_gdf, cities_gdf,country_gdf = read_shape_files()
    parsed_data=dict()
    print("creating place holders")
    parsed_data = country_placeholder(parsed_data)
    parsed_data = province_placeholder(parsed_data,province_gdf)
    parsed_data = district_placeholder(parsed_data,district_gdf)
    parsed_data = cities_placeholder(parsed_data,cities_gdf)
    print("populating data")
    parsed_data = populate_data(parsed_data,cities_gdf,dataset)
    print("saving populated data")
    with open("data/final_intermediate.json", 'w') as f:
        json.dump(parsed_data, f)
    print("aggregating data")
    get_country_details("Vietnam", parsed_data)
    print("writing data to file")
    with open("data/final_data.json", 'w') as f:
        json.dump(parsed_data, f)
    return "Successfully saved cities data"