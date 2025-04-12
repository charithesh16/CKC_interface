from datetime import datetime
from urllib import request

import pandas as pd
import plotly
from flask import Flask, render_template_string, jsonify, redirect, url_for, send_file, render_template
import json
import plotly.graph_objects as go
from folium.plugins import MarkerCluster

import map
import data_gen
from urllib.parse import urlparse
import util
import folium
import re
import text_insights

app = Flask(__name__)
mining_terms = ['oil', 'manganese', 'bismuth', 'titanium', 'bauxite', 'alloy', 'lead', 'zircon', 'chlorite', 'pit', 'extraction', 'lanthanide', 'phosphorites', 'graphite', 'peralkaline',
                'steel', 'tungsten', 'nitrogen', 'mineral', 'nickel', 'oxides', 'erbium', 'maser', 'eudialyte', 'garnet', 'quartz', 'alumina', 'bastnasite', 'barite', 'ree', 'phosphates',
                'thulium', 'scandium', 'ammonia', 'batteries', 'petrol', 'fluorite', 'allanite', 'open-pit', 'rare earth', 'silver', 'albite', 'quarrying', 'mining', 'radiation', 'titan',
                'uranium', 'dikes', 'cerium', 'loparite', 'gold', 'tin', 'magnetite', 'hastingsite', 'sand', 'xenotime', 'cadmium', 'synchesite', 'euxenite', 'molipden', 'lanthanides',
                'zirconium', 'hydrothermal', 'mines', 'minerals', 'chromite', 'carbonatite', 'drill', 'radioactive', 'lutetium', 'phosphorite', 'biotite', 'marble', 'promethium', 'vermiculite',
                'petroleum', 'silica', 'magmatic', 'chromate', 'zinc', 'iron', 'lasers', 'apatite', 'mercury', 'mine', 'plagioclase', 'metal', 'ores', 'parisite', 'radionuclide', 'masers',
                'halophosphors', 'radioactivity', 'carbonatites', 'bastnaesite', 'chondrite', 'magnet', 'yttrium', 'lithium', 'antimony', 'ytterbium', 'epidote', 'coal', 'titanite', 'rutile', 'chromium',
                'serpentine', 'cheralite', 'deposits', 'lanthanum', 'neodymium', 'terbium', 'ilmenite', 'pyroxene', 'radium', 'rare-earth', 'superconductors', 'praseodymium', 'phosphors', 'europium',
                'limestone', 'hree', 'holmium', 'critical minerals', 'copper', 'amphibole', 'laser', 'samarium', 'deposit', 'igneous', 'monazite', 'quartzite', 'dysprosium', 'lree', 'gadolinium', 'mica',
                'catalystxenotime', 'calcite','cobalt']
exclude_keys = set(["coordinates","keywords","articles","locations","row_count","keyword_count","emptyLocations","emptyKeywords"])

def get_district_data(country,province,district):
    global parsed_data
    row_count = 0
    keyword_count = 0
    keywords={}
    articles = {}
    for city in parsed_data[country][province][district].keys():
        city_data = parsed_data[country][province][district][city]
        row_count += city_data["row_count"]
        keyword_count += city_data["keyword_count"]
        for keyword,count in city_data["keywords"].items():
            if keyword not in keywords:
                keywords[keyword] = 0
            keywords[keyword] += count
        articles.update(city_data["articles"])
    parsed_data[country][province][district]["row_count"] = row_count
    parsed_data[country][province][district]["keyword_count"] = keyword_count
    parsed_data[country][province][district]["articles"] = articles
    parsed_data[country][province][district]["keywords"] = keywords
    return row_count,keyword_count,articles,keywords

def get_province_data(country,province):
    global parsed_data
    row_count = 0
    keyword_count = 0
    keywords = {}
    articles = {}
    for district in parsed_data[country][province].keys():
        rc,kc,ar,kw=get_district_data(country,province,district)
        row_count += rc
        keyword_count += kc
        keywords.update(kw)
        articles.update(ar)
    parsed_data[country][province]["row_count"] = row_count
    parsed_data[country][province]["keyword_count"] = keyword_count
    parsed_data[country][province]["articles"] = articles
    parsed_data[country][province]["keywords"] = keywords
    return row_count,keyword_count,articles,keywords

def get_country_details(country_name):
    global parsed_data
    row_count = 0
    keyword_count = 0
    keywords = {}
    articles = {}
    for province in parsed_data[country_name].keys():
        rc,kc,ar,kw=get_province_data(country_name,province)
        row_count += rc
        keyword_count += kc
        keywords.update(kw)
        articles.update(ar)
    parsed_data[country_name]["row_count"] = row_count
    parsed_data[country_name]["keyword_count"] = keyword_count
    parsed_data[country_name]["articles"] = articles
    parsed_data[country_name]["keywords"] = keywords
    return row_count,keyword_count,articles,keywords


def extract_domain(data):
    try:
        # Parse the URL
        url = data["source"]
        parsed_url = urlparse(url)
        # If the URL has a scheme and netloc, extract the domain
        if parsed_url.scheme and parsed_url.netloc:
            return parsed_url.netloc
        else:
            # If it's not a valid web URL, return the original input
            # return f"Journal : {data['subject']} Source: {data['source']}"
            return "Journals"
    except Exception as e:
        # In case of any unexpected errors, return the original input
        # print(data)
        # return f"Journal : {data['subject']} Source: {data['source']}"
        return "Journals"


# Add to app.py
from io import BytesIO
import xlsxwriter


@app.route('/download_data')
def download_data():
    # Get filter parameters
    search_term = request.args.get('search_term', '').lower()
    columns = request.args.getlist('columns')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Get location parameters
    country = request.args.get('country')
    province = request.args.get('province')
    district = request.args.get('district')

    # Filter data based on parameters
    filtered_data = filter_data(parsed_data, search_term if search_term else None,
                                columns if columns else None,
                                datetime.strptime(start_date, "%m/%d/%Y") if start_date else None,
                                datetime.strptime(end_date, "%m/%d/%Y") if end_date else None)


    # Get articles based on location hierarchy
    if district:
        articles = filtered_data[country][province][district].get('articles', {})
    elif province:
        articles = filtered_data[country][province].get('articles', {})
    else:
        articles = filtered_data[country].get('articles', {})

    # TODO after getting data for for above params check for keyword
    keyword = request.args.get('keyword',None)
    if None:
        temp = []
        for article in articles:
            if keyword in article["keywords"]:
                temp.append(articles)
        articles = temp

    # Create Excel file in memory with options to handle special values
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {
        'nan_inf_to_errors': True,
        'strings_to_numbers': False,
        'strings_to_formulas': False
    })
    worksheet = workbook.add_worksheet()

    # Add a format for text cells
    text_format = workbook.add_format()
    text_format.set_num_format('@')

    # Write headers
    headers = ['source','sentence', 'context', 'date', 'title', 'subject','keywords','ner_locations','companies','title','exact match locations','ad1','ad2','ad3']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)

    # Write data with proper handling of special values
    for row, article in enumerate(articles, start=1):
        for col, field in enumerate(headers):
            value = article.get(field, '')

            # Handle different value types
            if value is None:
                value = ''
            elif isinstance(value, (int, float)) and (pd.isna(value) or pd.isinf(value)):
                value = ''
            elif isinstance(value, str) and value.startswith('='):
                # Prevent formula injection by prefixing with single quote
                value = f"'{value}"

            # Write the value with text format to prevent auto-conversion
            worksheet.write(row, col, value, text_format)

    # Adjust column widths
    for col, header in enumerate(headers):
        worksheet.set_column(col, col, 20)  # Set width to 20 for all columns

    workbook.close()
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='articles_data.xlsx'
    )

def create_stacked_bar_chart(data):
    records = [{"url": data["source"], "date": pd.to_datetime(data["date"]), "domain": extract_domain(data)}
               for data in data["articles"]]
    df = pd.DataFrame(records)
    df = df.drop_duplicates(subset=['url'])
    # print(df.head())
    df['year'] = df['date'].dt.year
    article_counts = df.groupby(['year', 'domain']).size().unstack(fill_value=0)

    # Create a plotly figure
    fig = go.Figure()
    seen_urls = set()
    # Create articles dict grouped by year and domain
    articles_by_year_domain = {}
    for values in data["articles"]:
        url = values["source"]
        if url not in seen_urls:
            year = pd.to_datetime(values["date"]).year
            domain = extract_domain(values)
            if year not in articles_by_year_domain:
                articles_by_year_domain[year] = {}
            if domain not in articles_by_year_domain[year]:
                articles_by_year_domain[year][domain] = []
            if domain == "Journals" and pd.notna(values['subject']):
                articles_by_year_domain[year][domain].append(values['subject'])
            else:
                articles_by_year_domain[year][domain].append(url)
            seen_urls.add(url)

    # Create a stacked bar chart with custom hover data
    for domain in article_counts.columns:
        hover_texts = []
        for year in article_counts.index:
            count = article_counts.loc[year, domain]
            urls = articles_by_year_domain.get(year, {}).get(domain, [])
            hover_texts.append(f"Year: {year}<br>Domain: {domain}<br>Articles: {count}")

        fig.add_trace(go.Bar(
            x=article_counts.index,
            y=article_counts[domain],
            name=domain,
            hovertext=hover_texts,
            hoverinfo='text',
            customdata=[[year, domain] for year in article_counts.index]
        ))

    # Update layout
    fig.update_layout(
        barmode='stack',
        title="Number of Articles by Year and Domain",
        xaxis_title="Year",
        yaxis_title="Number of Articles",
        legend_title="Domain",
        height=500,
        # Add click event handling
        clickmode='event'
    )

    # Create a dictionary with all article data
    article_data = {
        str(year): {
            domain: articles_by_year_domain[year][domain]
            for domain in articles_by_year_domain[year]
        }
        for year in articles_by_year_domain
    }

    # Convert figures to JSON
    graph_json = json.dumps({
        'figure': fig.to_dict(),
        'article_data': article_data
    }, cls=plotly.utils.PlotlyJSONEncoder)

    return graph_json

@app.route("/spatial/<country>")
def get_country(country):
    global parsed_data
    global data
    data=None
    if request.args:
        # filter data and assign new data to data
        search_term = request.args.get('search_term','').lower()
        if len(search_term)==0:
            search_term = None
        columns = request.args.getlist('columns')
        if len(columns)==0:
            columns = None
        start_date = request.args.get('start_date',None)
        end_date = request.args.get('end_date',None)
        if start_date:
            start_date = datetime.strptime(start_date,"%m/%d/%Y")
        if end_date:
            end_date = datetime.strptime(end_date,"%m/%d/%Y")
        data = filter_data(parsed_data,search_term,columns,start_date,end_date)
    else:
        data = parsed_data

    if(data['Vietnam']['row_count']==0):
        return "No Data"

    # print(data)
    query_string = "?"+request.query_string.decode('utf-8')
    map_html, companies = map.get_country_map(data, country,query_string if query_string!="?" else "")
    graph_json = create_stacked_bar_chart(data[country])
    text_insights.get_word_graph(data,country)

    return render_template('index.html',
                           map_html=map_html,
                           name=country,
                           data=data[country],
                           companies=companies,
                           graph_json=graph_json,
                           request=request,
                           image_name="graph.png",
                           word_cloud_image="wordcloud.png"
                           )


def filter_data(data,search_term,columns,start_date,end_date):
    return data_gen.filter_data(data,search_term,columns,start_date,end_date)

@app.route("/spatial/<country>/<province>")
def get_province(country,province):
    global parsed_data
    data = None
    if request.args:
        # filter data and assign new data to data
        search_term = request.args.get('search_term', '').lower()
        if len(search_term) == 0:
            search_term = None
        columns = request.args.getlist('columns')
        if len(columns) == 0:
            columns = None
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        if start_date:
            start_date = datetime.strptime(start_date, "%m/%d/%Y")
        if end_date:
            end_date = datetime.strptime(end_date, "%m/%d/%Y")
        data = filter_data(parsed_data, search_term, columns, start_date, end_date)
    else:
        data = parsed_data
    if (data['Vietnam'][province]['row_count'] == 0):
        return "No Data"
    # print(data)
    query_string = "?" + request.query_string.decode('utf-8')
    map_html, companies = map.get_province_map(data, country, province,query_string if query_string!="?" else "")
    graph_json = create_stacked_bar_chart(data[country][province])
    text_insights.get_word_graph(data, country,province)
    return render_template('index.html',
                           map_html=map_html,
                           name=province,
                           data=data[country][province],
                           companies=companies,
                           graph_json=graph_json,
                            image_name="graph.png",
                            word_cloud_image = "wordcloud.png"
                           )
@app.route("/spatial/<country>/<province>/<district>")
def get_district(country,province,district):
    global parsed_data
    data = None
    if request.args:
        # filter data and assign new data to data
        search_term = request.args.get('search_term', '').lower()
        if len(search_term) == 0:
            search_term = None
        columns = request.args.getlist('columns')
        if len(columns) == 0:
            columns = None
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        if start_date:
            start_date = datetime.strptime(start_date, "%m/%d/%Y")
        if end_date:
            end_date = datetime.strptime(end_date, "%m/%d/%Y")
        data = filter_data(parsed_data, search_term, columns, start_date, end_date)
    else:
        data = parsed_data
    if (data['Vietnam'][province][district]['row_count'] == 0):
        return "No Data"
    query_string = "?" + request.query_string.decode('utf-8')
    map_html, companies = map.get_district_map(data, country, province, district,query_string if query_string!="?" else "")
    graph_json = create_stacked_bar_chart(data[country][province][district])
    text_insights.get_word_graph(data, country, province,district)
    return render_template('index.html',
                           map_html=map_html,
                           name=district,
                           data=data[country][province][district],
                           companies=companies,
                           graph_json=graph_json,image_name="graph.png",
                            word_cloud_image = "wordcloud.png")


@app.route('/generatedata')
def generatedata():
    data_gen.generate_data()
    return "Success"
@app.route("/aggregatedata")
def aggregate_data():
    parsed_data = None
    with open("data/aggregated_data.json", "r") as f:
        parsed_data = json.load(f)
    data_gen.get_country_details("Vietnam",parsed_data)
    with open("data/aggregated_data.json", "w") as t:
        json.dump(parsed_data,t)
    print("done")

# Add these imports at the top of app.py
from collections import Counter
from flask import request

@app.route("/keywords")
def show_keywords():
    # Get all keywords across all levels with their total counts
    all_keywords = Counter()
    provinces_by_keyword = {}

    for province in parsed_data["Vietnam"].keys():
        if province not in ["coordinates", "keywords", "articles", "locations", "row_count", "keyword_count","emptyLocations","emptyKeywords"]:
            province_data = parsed_data["Vietnam"][province]
            for keyword, count in province_data["keywords"].items():
                all_keywords[keyword] += count
                if keyword not in provinces_by_keyword:
                    provinces_by_keyword[keyword] = []
                provinces_by_keyword[keyword].append(province)

    # add non location articles
    for article in parsed_data["Vietnam"]["emptyLocations"]:
        keywords = str(article["keywords"]).split(", ")
        for keyword in keywords:
            all_keywords[keyword]+=1


    # Sort keywords by count in descending order
    sorted_keywords = sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)

    return render_template('keywords.html',
                           keywords=sorted_keywords,
                           provinces_by_keyword=provinces_by_keyword)

def generate_querystring(search_term, columns, start_date, end_date):
    s = "?"
    params = []

    if search_term:
        params.append(f"search_term={search_term}")

    if columns:
        params.extend([f"columns={column}" for column in columns])

    if start_date:
        params.append(f"start_date={start_date.strftime('%m/%d/%Y')}")

    if end_date:
        params.append(f"end_date={end_date.strftime('%m/%d/%Y')}")

    # Join all non-null parameters with '&'
    if s=="?": return None
    s += "&".join(params)
    return None if s=="&?" else s



@app.route("/keyword/<keyword>/country")
def show_keyword_country(keyword):
    global parsed_data
    data = None
    query_string=None
    if request.args:
        # filter data and assign new data to data
        search_term = keyword.lower()
        if len(search_term) == 0:
            search_term = None
        columns = ['keywords']
        if len(columns) == 0:
            columns = None
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        if start_date:
            start_date = datetime.strptime(start_date, "%m/%d/%Y")
        if end_date:
            end_date = datetime.strptime(end_date, "%m/%d/%Y")
        data = filter_data(parsed_data, search_term, columns, start_date, end_date)
        query_string = generate_querystring(search_term, columns, start_date, end_date)
    else:
        data = parsed_data

    if (data['Vietnam']['row_count'] == 0):
        return "No Data"

    # print(data)


    locations = []
    articles = {}
    provinces_data = []

    # Collect data for each province
    for province in data["Vietnam"].keys():
        if province not in ["coordinates", "keywords", "articles", "locations", "row_count", "keyword_count","emptyLocations","emptyKeywords"]:
            province_data = data["Vietnam"][province]
            if keyword in province_data["keywords"]:
                provinces_data.append({
                    "name": province,
                    "count": province_data["keywords"][keyword],
                    "coordinates": province_data["coordinates"]
                })

    # add non location count
    no_location_count = {"name":"Vietnam","coordinates":data["Vietnam"]["coordinates"],"count":0}
    for article in data["Vietnam"]["emptyLocations"]:
        kws = str(article['keywords']).split(",")
        for kw in kws:
            if kw.strip().lower() == keyword:
                no_location_count["count"]+=1



    # Create the map
    m = folium.Map(location=[14.0583, 108.2772], zoom_start=6)
    m = map.add_active_economic_sites(m)
    # Add satellite layer
    util.get_satellite_map(m)
    util.add_country_boundary(m)
    util.add_province_boundary(m)

    # Add markers for provinces
    marker_cluster = MarkerCluster(name=f"{keyword} Locations")
    for prov in provinces_data:
        url = f"/keyword/{keyword}/province?province={prov['name']}"
        if query_string:
            url += f"&{query_string}"
        popup_content = f"""
        <b>{prov['name']}</b><br>
        {keyword} count: {prov['count']}<br>
        <a href="{url}" target="_blank">View Province Details</a>
        """
        folium.Marker(
            location=prov['coordinates'],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=prov['name']
        ).add_to(marker_cluster)
    # add no location count

    folium.Marker(location=no_location_count['coordinates'],
                  popup=folium.Popup(f"""
        <b>Vietnam ( no location tagged )</b>
        {keyword} count: {no_location_count['count']}<br>
        """,max_width=500),
            tooltip="Vietnam ( no location tagged )",
                  icon=folium.Icon(color="red")).add_to(marker_cluster)

    marker_cluster.add_to(m)
    folium.LayerControl().add_to(m)
    graph_json = create_stacked_bar_chart(data["Vietnam"])

    return render_template(
        'keyword_locations.html',
        map_html=m._repr_html_(),
        keyword=keyword,
        level='country',
        location_count=len(provinces_data),
        provinces=sorted([p["name"] for p in provinces_data]),
        data=data["Vietnam"],
        graph_json=graph_json,
    )

@app.route("/keyword/<keyword>/province")
def show_keyword_province(keyword):
    global parsed_data
    data = None
    query_string = None
    if request.args:
        # filter data and assign new data to data
        search_term = keyword.lower()
        if len(search_term) == 0:
            search_term = None
        columns = ['keywords']
        if len(columns) == 0:
            columns = None
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        if start_date:
            start_date = datetime.strptime(start_date, "%m/%d/%Y")
        if end_date:
            end_date = datetime.strptime(end_date, "%m/%d/%Y")
        data = filter_data(parsed_data, search_term, columns, start_date, end_date)
        query_string = generate_querystring(search_term, columns, start_date, end_date)
    else:
        data = parsed_data

    if (data['Vietnam']['row_count'] == 0):
        return "No Data"

    # print(data)


    province = request.args.get('province')

    if (data['Vietnam'][province]['row_count'] == 0):
        return "No Data"

    if not province or province not in data["Vietnam"]:
        return redirect(url_for('show_keyword_country', keyword=keyword))

    districts_data = []
    articles = []

    # Collect data for each district in the province
    province_data = data["Vietnam"][province]
    for district in province_data.keys():
        if district not in ["coordinates", "keywords", "articles", "locations", "row_count", "keyword_count"]:
            district_data = province_data[district]
            if keyword in district_data["keywords"]:
                districts_data.append({
                    "name": district,
                    "count": district_data["keywords"][keyword],
                    "coordinates": district_data["coordinates"]
                })
                if "articles" in district_data:
                    articles.extend(district_data["articles"])

    # Create the map
    m = folium.Map(location=province_data["coordinates"], zoom_start=8)
    m = map.add_active_economic_sites(m)
    # Add satellite layer
    util.get_satellite_map(m)

    # Add province boundary
    util.add_country_boundary(m)
    gdf_province = util.add_province_boundary(m, province_name=province, style_options={
        'fillColor': 'transparent',
        'color': '#0000FF',
        'weight': 3,
        'fillOpacity': 0.1
    })
    # util.add_province_boundary(m, province_name=province)
    util.add_district_boundary(m, province_name=province)
    m.fit_bounds(util.get_bounds(gdf_province))

    no_location_count = {"name": "Vietnam", "coordinates": data["Vietnam"]["coordinates"], "count": 0}
    for article in data["Vietnam"]["emptyLocations"]:
        kws = str(article['keywords']).split(",")
        for kw in kws:
            if kw.strip().lower() == keyword:
                no_location_count["count"] += 1

    # Add markers for districts
    marker_cluster = MarkerCluster(name=f"{keyword} Locations")
    for dist in districts_data:
        url = f"/keyword/{keyword}/district?province={province}&district={dist['name']}"
        if query_string:
            url += f"&{query_string}"
        popup_content = f"""
        <b>{dist['name']}</b><br>
        {keyword} count: {dist['count']}<br>
        <a href="{url}" target="_blank">View District Details</a>
        """
        folium.Marker(
            location=dist['coordinates'],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=dist['name']
        ).add_to(marker_cluster)

        # add no location count

    folium.Marker(location=no_location_count['coordinates'],
                  popup=folium.Popup(f"""
        <b>Vietnam ( no location tagged )</b>
        {keyword} count: {no_location_count['count']}<br>
        """, max_width=500),
                  tooltip="Vietnam ( no location tagged )",
                  icon=folium.Icon(color="red")).add_to(marker_cluster)

    marker_cluster.add_to(m)
    folium.LayerControl().add_to(m)

    # Create the stacked bar chart for articles
    # graph_json = create_stacked_bar_chart({"articles": articles}) if articles else None
    graph_json = create_stacked_bar_chart(data["Vietnam"][province])

    return render_template(
        'keyword_locations.html',
        map_html=m._repr_html_(),
        keyword=keyword,
        level='province',
        province=province,
        location_count=len(districts_data),
        article_count=len(articles),
        graph_json=graph_json,
        data = data["Vietnam"][province],
        districts=sorted([d["name"] for d in districts_data])
    )

@app.route("/keyword/<keyword>/district")
def show_keyword_district(keyword):
    global parsed_data
    data = None
    query_string = None
    if request.args:
        # filter data and assign new data to data
        search_term = keyword.lower()
        if len(search_term) == 0:
            search_term = None
        columns = ['keywords']
        if len(columns) == 0:
            columns = None
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        if start_date:
            start_date = datetime.strptime(start_date, "%m/%d/%Y")
        if end_date:
            end_date = datetime.strptime(end_date, "%m/%d/%Y")
        data = filter_data(parsed_data, search_term, columns, start_date, end_date)
        query_string = generate_querystring(search_term, columns, start_date, end_date)
    else:
        data = parsed_data



    province = request.args.get('province')
    district = request.args.get('district')
    if (data['Vietnam'][province][district]['row_count'] == 0):
        return "No Data"

    if not province or not district or \
            province not in parsed_data["Vietnam"] or \
            district not in parsed_data["Vietnam"][province]:
        return redirect(url_for('show_keyword_country', keyword=keyword))

    locations = []
    articles = []

    # Collect data for each city in the district
    district_data = data["Vietnam"][province][district]
    for city in district_data.keys():
        if city not in ["coordinates", "keywords", "articles", "locations", "row_count", "keyword_count","emptyLocations","emptyKeywords"]:
            city_data = district_data[city]
            if keyword in city_data["keywords"]:
                for loc_name, coords in city_data["locations"].items():
                    locations.append({
                        "name": loc_name,
                        "city": city,
                        "coordinates": coords,
                        "count": city_data["keywords"][keyword]
                    })
                if "articles" in city_data:
                    articles.extend(city_data["articles"])

    # Create the map
    m = folium.Map(location=district_data["coordinates"], zoom_start=10)
    m = map.add_active_economic_sites(m)
    no_location_count = {"name": "Vietnam", "coordinates": data["Vietnam"]["coordinates"], "count": 0}
    for article in data["Vietnam"]["emptyLocations"]:
        kws = str(article['keywords']).split(",")
        for kw in kws:
            if kw.strip().lower() == keyword:
                no_location_count["count"] += 1


    # Add satellite layer
    util.get_satellite_map(m)

    # Add boundaries
    util.add_country_boundary(m)
    gdf_province = util.add_province_boundary(m, province_name=province, style_options={
        'fillColor': 'transparent',
        'color': '#0000FF',
        'weight': 3,
        'fillOpacity': 0.1
    })
    util.add_district_boundary(m, province_name=province, district_name=district)
    util.add_city_boundary(m, province_name=province, district_name=district)

    # Add markers for locations
    marker_cluster = MarkerCluster(name=f"{keyword} Locations")
    for loc in locations:
        popup_content = f"""
        {loc['city']}<br>
        {keyword} count: {loc['count']}
        """
        folium.Marker(
            location=loc['coordinates'],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=loc['city']
        ).add_to(marker_cluster)

    folium.Marker(location=no_location_count['coordinates'],
                  popup=folium.Popup(f"""
            <b>Vietnam ( no location tagged )</b>
            {keyword} count: {no_location_count['count']}<br>
            """, max_width=500),
                  tooltip="Vietnam ( no location tagged )",
                  icon=folium.Icon(color="red")).add_to(marker_cluster)

    marker_cluster.add_to(m)
    folium.LayerControl().add_to(m)

    # Create the stacked bar chart for articles
    # graph_json = create_stacked_bar_chart({"articles": articles}) if articles else None
    graph_json = create_stacked_bar_chart(data["Vietnam"][province][district])

    return render_template(
        'keyword_locations.html',
        map_html=m._repr_html_(),
        keyword=keyword,
        level='district',
        province=province,
        district=district,
        location_count=len(locations),
        article_count=len(articles),
        data=data["Vietnam"][province][district],
        graph_json=graph_json
    )

@app.route('/v1/populateKeywords/')
def populateKeywords():
    # Function to check and extract whole word keywords in each sentence
    def extract_keywords(sentence):
        keywords = [term for term in mining_terms if re.search(r'\b' + re.escape(term) + r'\b', str(sentence), re.IGNORECASE)]
        return ', '.join(keywords) if keywords else None
    data = pd.read_excel('./data/pdf/pdf_final.xlsx')
    data['keywords'] = data['sentence'].apply(extract_keywords)
    data.to_excel('./data/pdf/final_keywords.xlsx', index=False)
    return "Keywords populated successfully"

@app.route('/')
def home():
    global exclude_keys
    # Calculate statistics for the overview section
    total_provinces = sum(1 for key in parsed_data["Vietnam"].keys()
                          if
                          key not in exclude_keys)

    # Get total unique keywords
    all_keywords = set()
    for province in parsed_data["Vietnam"].keys():
        if province not in exclude_keys:
            province_data = parsed_data["Vietnam"][province]
            all_keywords.update(province_data.get("keywords", {}).keys())

    # Get total articles
    total_articles = len(parsed_data["Vietnam"].get("articles", {}))
    print("non location tagged ",len(parsed_data["Vietnam"]["emptyLocations"]))

    return render_template('home.html',
                           total_provinces=total_provinces,
                           total_keywords=len(all_keywords),
                           total_articles=total_articles)

parsed_data = None
data = None
if __name__ == '__main__':
    with open("data/final_data.json", "r") as f:
        parsed_data = json.load(f)
    app.run(host='0.0.0.0', port=8080, debug=True)