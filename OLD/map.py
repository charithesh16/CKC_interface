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
# import util
# exclude_keys = set(["coordinates","keywords","articles","locations","row_count","keyword_count"])
# def get_country_map(parsed_data,country_name):
#     global exclude_keys
#     m = folium.Map(location=[14.0583, 108.2772],zoom_start=5)
#     util.get_satellite_map(m)
#     util.add_country_layer(m)
#     util.add_province_layer(m)
#     markers = MarkerCluster(name="Country Level", show=True)
#     for province,data in parsed_data[country_name].items():
#         if province not in exclude_keys and data["row_count"] >0:
#             url = "/spatial/"+country_name+"/"+province
#             popup_content = util.create_popup_content(url,province)
#             folium.Marker(
#                 location=data['coordinates'],
#                 popup=folium.Popup(popup_content, max_width=300),
#                 tooltip=province
#             ).add_to(markers)
#     markers.add_to(m)
#     folium.LayerControl().add_to(m)
#     map_html = m._repr_html_()
#     return map_html
#
#
# def get_province_map(parsed_data,country, province):
#     province_data = parsed_data[country][province]
#     m = folium.Map(location=province_data['coordinates'], zoom_start=5)
#     util.get_satellite_map(m)
#     util.add_country_layer(m)
#     util.add_district_layer(m)
#     markers = MarkerCluster(name="Province Level", show=True)
#     global exclude_keys
#     for district, data in province_data.items():
#         if district not in exclude_keys and data["row_count"] >0:
#             url = "/spatial/" + country + "/" + province+"/"+district
#             popup_content = util.create_popup_content(url, district)
#             folium.Marker(
#                 location=data['coordinates'],
#                 popup=folium.Popup(popup_content, max_width=300),
#                 tooltip=district
#             ).add_to(markers)
#     markers.add_to(m)
#     folium.LayerControl().add_to(m)
#     map_html = m._repr_html_()
#     return map_html
#
#
# def get_district_map(parsed_data, country, province, district):
#     district_data = parsed_data[country][province][district]
#     m = folium.Map(location=district_data['coordinates'], zoom_start=5)
#     util.get_satellite_map(m)
#     util.add_country_layer(m)
#     util.add_province_layer(m)
#     util.add_district_layer(m)
#     util.add_city_layer(m)
#     markers = MarkerCluster(name="District Level", show=True)
#     global exclude_keys
#     for city, data in district_data.items():
#         if city not in exclude_keys and data["row_count"] >0:
#             url = "/spatial/" + country + "/" + province + "/" + district+"/"+city
#             # popup_content = util.create_popup_content(url, city)
#             popup_content = f'''
#     <b>{city}</b><br>
#     '''
#             for keyword,count in data["keywords"].items():
#                 popup_content += f'''<br>{keyword} : {count}'''
#             folium.Marker(
#                 location=data['coordinates'],
#                 popup=folium.Popup(popup_content, max_width=300),
#                 tooltip=city
#             ).add_to(markers)
#     markers.add_to(m)
#     folium.LayerControl().add_to(m)
#     map_html = m._repr_html_()
#     return map_html