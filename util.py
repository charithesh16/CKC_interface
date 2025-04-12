
import folium
import geopandas as gpd


def get_bounds(gdf_filtered):
    """Get the bounds of a geodataframe in the format Folium expects"""
    bounds = gdf_filtered.total_bounds
    return [[bounds[1], bounds[0]], [bounds[3], bounds[2]]]


def get_admin_region(shapefile_path, region_name, name_column):
    """Get specific admin region and its geometry"""
    gdf = gpd.read_file(shapefile_path)
    region = gdf[gdf[name_column] == region_name]
    return region


def clip_lower_admin_levels(higher_gdf, lower_shapefile):
    """Clip lower administrative level boundaries to higher level region"""
    lower_gdf = gpd.read_file(lower_shapefile)
    clipped = gpd.clip(lower_gdf, higher_gdf)
    return clipped


def add_country_boundary(m, style_options=None):
    if style_options is None:
        style_options = {
            'fillColor': 'transparent',
            'color': '#FF0000',  # Red
            'weight': 3,
            'fillOpacity': 0.1
        }

    gdf_country = gpd.read_file('./Vietnam_Shapefile/gadm41_VNM_shp/gadm41_VNM_0.shp')
    folium.GeoJson(
        gdf_country,
        style_function=lambda x: style_options
    ).add_to(m)
    return gdf_country


def add_province_boundary(m, province_name=None, style_options=None):
    if style_options is None:
        style_options = {
            'fillColor': 'transparent',
            'color': '#0000FF',  # Blue
            'weight': 2,
            'fillOpacity': 0.1
        }

    gdf_provinces = gpd.read_file('./Vietnam_Shapefile/gadm41_VNM_shp/gadm41_VNM_1.shp')

    if province_name:
        gdf_provinces = gdf_provinces[gdf_provinces['NAME_1'] == province_name]

    folium.GeoJson(
        gdf_provinces,
        style_function=lambda x: style_options
    ).add_to(m)
    return gdf_provinces


def add_district_boundary(m, province_name=None, district_name=None, style_options=None):
    if style_options is None:
        style_options = {
            'fillColor': 'transparent',
            'color': '#00FF00',  # Green
            'weight': 1.5,
            'fillOpacity': 0.1
        }

    gdf_districts = gpd.read_file('./Vietnam_Shapefile/gadm41_VNM_shp/gadm41_VNM_2.shp')

    if province_name:
        gdf_districts = gdf_districts[gdf_districts['NAME_1'] == province_name]
    if district_name:
        gdf_districts = gdf_districts[gdf_districts['NAME_2'] == district_name]

    if province_name:
        province_geom = get_admin_region(
            './Vietnam_Shapefile/gadm41_VNM_shp/gadm41_VNM_1.shp',
            province_name,
            'NAME_1'
        ).geometry.iloc[0]
        gdf_districts = gpd.clip(gdf_districts, province_geom)

    folium.GeoJson(
        gdf_districts,
        style_function=lambda x: style_options
    ).add_to(m)
    return gdf_districts


def add_city_boundary(m, province_name=None, district_name=None, style_options=None):
    if style_options is None:
        style_options = {
            'fillColor': 'transparent',
            'color': '#FFA500',  # Orange
            'weight': 1,
            'fillOpacity': 0.1
        }

    gdf_cities = gpd.read_file('./Vietnam_Shapefile/gadm41_VNM_shp/gadm41_VNM_3.shp')

    if province_name:
        gdf_cities = gdf_cities[gdf_cities['NAME_1'] == province_name]
    if district_name:
        gdf_cities = gdf_cities[gdf_cities['NAME_2'] == district_name]

    if province_name:
        province_geom = get_admin_region(
            './Vietnam_Shapefile/gadm41_VNM_shp/gadm41_VNM_1.shp',
            province_name,
            'NAME_1'
        ).geometry.iloc[0]
        gdf_cities = gpd.clip(gdf_cities, province_geom)

    if district_name:
        district_geom = get_admin_region(
            './Vietnam_Shapefile/gadm41_VNM_shp/gadm41_VNM_2.shp',
            district_name,
            'NAME_2'
        ).geometry.iloc[0]
        gdf_cities = gpd.clip(gdf_cities, district_geom)

    folium.GeoJson(
        gdf_cities,
        style_function=lambda x: style_options
    ).add_to(m)
    return gdf_cities


def get_satellite_map(m):
    tile = folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Esri Satellite',
        overlay=False,
        control=True
    ).add_to(m)


def create_popup_content(url, name):
    return f'''
    <b>{name}</b><br>
    <a href="{url}" target="_blank">View details</a>
    '''