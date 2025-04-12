#
# import folium.map
# import pandas as pd
# import folium
# from flask import Flask,render_template_string, jsonify, redirect, url_for, send_file
# import plotly.express as px
# import re
# import geopandas as gpd
# from shapely.geometry import Point
# from folium.plugins import MarkerCluster
# from wordcloud import WordCloud
# import io
# import base64
# import json
# import os
# from datetime import datetime
#
# def add_country_layer(m):
#     gdf_country = gpd.read_file('./Vietnam_Shapefile/gadm41_VNM_shp/gadm41_VNM_0.shp')
#      # Add the country boundaries
#     folium.GeoJson(
#         gdf_country,
#         style_function=lambda feature: {
#             'fillColor': 'transparent',
#             'color': 'red',
#             'weight': 2,
#             'fillOpacity': 0.5,
#         }
#     ).add_to(m)
#
# def add_province_layer(m):
#     gdf_country = gpd.read_file('./Vietnam_Shapefile/gadm41_VNM_shp/gadm41_VNM_1.shp')
#      # Add the province boundaries
#     folium.GeoJson(
#         gdf_country,
#         style_function=lambda feature: {
#             'fillColor': 'transparent',
#             'color': 'blue',
#             'weight': 2,
#             'fillOpacity': 0.5,
#         }
#     ).add_to(m)
#
# def add_district_layer(m):
#     gdf_country = gpd.read_file('./Vietnam_Shapefile/gadm41_VNM_shp/gadm41_VNM_2.shp')
#      # Add the province boundaries
#     folium.GeoJson(
#         gdf_country,
#         style_function=lambda feature: {
#             'fillColor': 'transparent',
#             'color': 'white',
#             'weight': 1,
#             'fillOpacity': 0.5,
#         }
#     ).add_to(m)
#
# def add_city_layer(m):
#     gdf_country = gpd.read_file('./Vietnam_Shapefile/gadm41_VNM_shp/gadm41_VNM_3.shp')
#      # Add the province boundaries
#     folium.GeoJson(
#         gdf_country,
#         style_function=lambda feature: {
#             'fillColor': 'transparent',
#             'color': 'white',
#             'weight': 0.25,
#             'fillOpacity': 0.5,
#         }
#     ).add_to(m)
#
# def get_satellite_map(m):
#     tile = folium.TileLayer(
#         tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
#         attr = 'Esri',
#         name = 'Esri Satellite',
#         overlay = False,
#         control = True
#         ).add_to(m)
#
# def add_markers(data,m,level):
#     markers = MarkerCluster(name=f"{level.capitalize()} Level", show=True)
#     for name, stats in data.items():
#             if stats['row_count'] > 0:
#                 popup_content = create_popup_content(level, name)
#                 folium.Marker(
#                     location=stats['coordinates'],
#                     popup=folium.Popup(popup_content, max_width=300),
#                     tooltip=name
#                 ).add_to(markers)
#
#
#     markers.add_to(m)
# def create_popup_content(url, name):
#     return f'''
#     <b>{name}</b><br>
#     <a href="{url}" target="_blank">View details</a>
#     '''

