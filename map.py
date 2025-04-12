import folium
from folium.plugins import MarkerCluster
import util
import pandas as pd
from shapely.geometry import Point
import geopandas as gpd
exclude_keys = set(["coordinates","keywords","articles","locations","row_count","keyword_count","emptyLocations","emptyKeywords"])

def add_company_markers(m, province_name=None, district_name=None):
    filtered_companies = {
        'metal': [],
        'non_metal': []
    }

    # Read company data
    metal_company_data = pd.read_csv('./data/companies/metal_ore_companies_full_with_lat_long.csv')
    metal_company_data = metal_company_data.dropna(subset=['Latitude', 'Longitude'])

    # Convert to GeoDataFrame for spatial operations
    metal_company_gdf = gpd.GeoDataFrame(
        metal_company_data,
        geometry=[Point(xy) for xy in zip(metal_company_data['Longitude'], metal_company_data['Latitude'])]
    )

    # Filter companies based on administrative boundaries
    if province_name:
        province_gdf = gpd.read_file('./Vietnam_Shapefile/gadm41_VNM_shp/gadm41_VNM_1.shp')
        province_boundary = province_gdf[province_gdf['NAME_1'] == province_name].geometry.iloc[0]
        metal_company_gdf = metal_company_gdf[metal_company_gdf.geometry.within(province_boundary)]

        if district_name:
            district_gdf = gpd.read_file('./Vietnam_Shapefile/gadm41_VNM_shp/gadm41_VNM_2.shp')
            district_boundary = district_gdf[
                (district_gdf['NAME_1'] == province_name) &
                (district_gdf['NAME_2'] == district_name)
                ].geometry.iloc[0]
            metal_company_gdf = metal_company_gdf[metal_company_gdf.geometry.within(district_boundary)]

    # Store filtered metal companies
    for _, row in metal_company_gdf.iterrows():
        filtered_companies['metal'].append({
            'name': row['Company Name'],
            'shortname':row['Doing Business As'],
            'industry': row['Industries']
        })

    # Add metal company markers
    metal_company_markers = MarkerCluster(name="Metal Ore Company Locations", show=True)
    for _, row in metal_company_gdf.iterrows():
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=f'''
            <b> Metallic</b> <br><br>
            <b>Company</b>: {row['Company Name']}<br>
            
            <b>Industry</b>: {row['Industries']}''',
            icon=folium.Icon(color='orange')
        ).add_to(metal_company_markers)
    metal_company_markers.add_to(m)

    # Read and process non-metal company data
    non_metal_company_data = pd.read_csv('./data/companies/non_metal_companies_with_lat_long.csv')
    non_metal_company_data = non_metal_company_data.dropna(subset=['Latitude', 'Longitude'])

    # Convert to GeoDataFrame
    non_metal_company_gdf = gpd.GeoDataFrame(
        non_metal_company_data,
        geometry=[Point(xy) for xy in zip(non_metal_company_data['Longitude'], non_metal_company_data['Latitude'])]
    )

    # Apply the same filtering
    if province_name:
        non_metal_company_gdf = non_metal_company_gdf[non_metal_company_gdf.geometry.within(province_boundary)]
        if district_name:
            non_metal_company_gdf = non_metal_company_gdf[non_metal_company_gdf.geometry.within(district_boundary)]

    for _, row in non_metal_company_gdf.iterrows():
        filtered_companies['non_metal'].append({
            'name': row['Company Name'],
            'shortname': row['Doing Business As'],
            'industry': row['Industries']
        })

    # Add non-metal company markers
    non_metal_company_markers = MarkerCluster(name="Non Metal Ore Company Locations", show=True)
    for _, row in non_metal_company_gdf.iterrows():
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=f'''
            <b> Non Metallic</b> <br><br>
            <b>Company</b>: {row['Company Name']}<br>
            
            <b>Industry</b>: {row['Industries']}''',
            icon=folium.Icon(color='orange')
        ).add_to(non_metal_company_markers)
    non_metal_company_markers.add_to(m)
    return filtered_companies


def add_active_economic_sites(m):
    # Read the shapefile containing Active Economic Sites points
    aes_sites = gpd.read_file('./AES_Points/ActiveEconomicSites.shp')
    print(aes_sites.head())
    # Create a feature group for AES markers
    aes_group = folium.FeatureGroup(name='Active Economic Sites')

    # Iterate through each point in the shapefile
    for idx, row in aes_sites.iterrows():
        # Extract coordinates (assuming the geometry is in EPSG:4326)
        lat = row.geometry.y
        lon = row.geometry.x

        # Create marker for each site
        folium.Marker(
            location=[lat, lon],
            popup=row['name'] if 'name' in row else 'Economic Site',  # Display site name if available
            icon=folium.Icon(color='red', icon='info-sign'),  # Custom icon for economic sites
        ).add_to(aes_group)

    # Add the feature group to the map
    aes_group.add_to(m)

    return m



def get_country_map(parsed_data, country_name,query_string):
    m = folium.Map(location=[14.0583, 108.2772], zoom_start=5)
    util.get_satellite_map(m)

    # Add only country boundary
    gdf_country = util.add_country_boundary(m)
    util.add_province_boundary(m, style_options={
        'fillColor': 'transparent',
        'color': '#0000FF',  # Blue
        'weight': 1.5,  # Thinner than country boundary
        'fillOpacity': 0.1
    })


    # Add markers
    markers = MarkerCluster(name="Country Level", show=True)
    global exclude_keys

    for province, data in parsed_data[country_name].items():
        if province not in exclude_keys and data["row_count"] > 0:
            url = f"/spatial/{country_name}/{province}{query_string}"
            popup_content = util.create_popup_content(url, province)
            folium.Marker(
                location=data['coordinates'],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=province
            ).add_to(markers)

    markers.add_to(m)
    companies = add_company_markers(m)
    # m.add_child(company_markers)
    m = add_active_economic_sites(m)

    folium.LayerControl().add_to(m)

    # Fit bounds to country
    m.fit_bounds(util.get_bounds(gdf_country))

    return m._repr_html_(), companies


def get_province_map(parsed_data, country, province,query_string):
    province_data = parsed_data[country][province]
    m = folium.Map(location=province_data['coordinates'], zoom_start=8)
    util.get_satellite_map(m)
    util.add_country_boundary(m)

    # Add only province boundary and its districts
    gdf_province = util.add_province_boundary(m, province_name=province, style_options={
        'fillColor': 'transparent',
        'color': '#0000FF',
        'weight': 3,
        'fillOpacity': 0.1
    })

    util.add_district_boundary(m, province_name=province)

    # Add markers
    markers = MarkerCluster(name="Province Level", show=True)
    global exclude_keys

    for district, data in province_data.items():
        if district not in exclude_keys and data["row_count"] > 0:
            url = f"/spatial/{country}/{province}/{district}{query_string}"
            popup_content = util.create_popup_content(url, district)
            folium.Marker(
                location=data['coordinates'],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=district
            ).add_to(markers)

    markers.add_to(m)
    companies = add_company_markers(m, province)
    m = add_active_economic_sites(m)
    folium.LayerControl().add_to(m)

    # Fit bounds to province
    m.fit_bounds(util.get_bounds(gdf_province))

    return m._repr_html_(), companies


def get_district_map(parsed_data, country, province, district,query_string):
    district_data = parsed_data[country][province][district]
    m = folium.Map(location=district_data['coordinates'], zoom_start=10)
    util.get_satellite_map(m)

    # Add only district boundary and its cities
    util.add_country_boundary(m)
    util.add_province_boundary(m, province_name=province, style_options={
        'fillColor': 'transparent',
        'color': '#0000FF',
        'weight': 3,
        'fillOpacity': 0.1
    })
    gdf_district = util.add_district_boundary(
        m,
        province_name=province,
        district_name=district,
        style_options={
            'fillColor': 'transparent',
            'color': '#00FF00',
            'weight': 3,
            'fillOpacity': 0.1
        }
    )

    util.add_city_boundary(m, province_name=province, district_name=district)

    # Add markers
    markers = MarkerCluster(name="District Level", show=True)
    global exclude_keys

    for city, data in district_data.items():
        if city not in exclude_keys and data["row_count"] > 0:
            popup_content = f'''
            <b>{city}</b><br>
            '''
            for keyword, count in data["keywords"].items():
                popup_content += f'''<br>{keyword} : {count}'''

            folium.Marker(
                location=data['coordinates'],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=city
            ).add_to(markers)

    markers.add_to(m)
    companies = add_company_markers(m, province, district)
    m = add_active_economic_sites(m)
    folium.LayerControl().add_to(m)

    # Fit bounds to district
    m.fit_bounds(util.get_bounds(gdf_district))

    return m._repr_html_(), companies