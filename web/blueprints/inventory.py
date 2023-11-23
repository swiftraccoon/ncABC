from flask import Blueprint, render_template, request, jsonify
import sqlite3
import os
import pandas as pd
import plotly.express as px
from sklearn.linear_model import LinearRegression
import numpy as np

inventory_bp = Blueprint('inventory_bp', __name__)

# Global cache dictionary
cache = {}


def generate_cache_key(date1, date2, suppliers):
    supplier_key = '-'.join(sorted(suppliers)) if suppliers else 'all'
    return f"{date1}-{date2}-{supplier_key}"


def generate_cache_key_date_range(start_date, end_date, suppliers):
    supplier_key = '-'.join(sorted(suppliers)) if suppliers else 'all'
    return f"range-{start_date}-{end_date}-{supplier_key}"


def get_db_connection():
    conn = sqlite3.connect(os.getenv('DB_FILE_PATH'))
    conn.row_factory = sqlite3.Row
    return conn


def compare_inventory_data(date1, date2, suppliers=None):
    key = generate_cache_key(date1, date2, suppliers)

    if key in cache:
        print("Fetching results from cache")
        return cache[key]

    conn = get_db_connection()
    query = '''SELECT h1.nc_code, i.brand_name, h1.total_available as total_available_date1,
               h2.total_available as total_available_date2, s.name as supplier_name
               FROM historical_inventory h1
               JOIN historical_inventory h2 ON h1.nc_code = h2.nc_code
               JOIN inventory i ON h1.nc_code = i.nc_code'''

    # Adjusting JOIN based on suppliers parameter
    if suppliers and 'all' not in suppliers:
        query += ' INNER JOIN suppliers s ON i.supplier_id = s.id'
        query += ' WHERE h1.date = ? AND h2.date = ? AND h1.total_available != h2.total_available'
        placeholders = ', '.join('?' * len(suppliers))
        query += f" AND s.name IN ({placeholders})"
        params = [date1, date2] + suppliers
    else:
        query += ' LEFT JOIN suppliers s ON i.supplier_id = s.id'
        query += ' WHERE h1.date = ? AND h2.date = ? AND h1.total_available != h2.total_available'
        params = [date1, date2]

    cursor = conn.cursor()
    cursor.execute(query, params)
    raw_rows = cursor.fetchall()
    conn.close()

    # Convert rows to dictionaries and calculate percentage change
    rows = []
    for row in raw_rows:
        dict_row = dict(row)
        total_available_date1 = dict_row['total_available_date1']
        total_available_date2 = dict_row['total_available_date2']
        dict_row['percentage_change'] = abs(
            total_available_date2 - total_available_date1) / (total_available_date1 + 1) * 100
        rows.append(dict_row)

    # Sort rows by percentage change
    rows.sort(key=lambda x: x['percentage_change'], reverse=True)

    # Cache the results
    cache[key] = rows
    return rows


def compare_inventory_data_date_range(start_date, end_date, suppliers=None):
    # Generate a unique cache key for date range
    key = generate_cache_key_date_range(start_date, end_date, suppliers)

    # Check if the results are in cache
    if key in cache:
        print("Fetching results from cache")
        return cache[key]
    conn = get_db_connection()
    cursor = conn.cursor()

    # SQL query to fetch inventory data between start_date and end_date
    query = '''SELECT h1.nc_code, i.brand_name, h1.date, h1.total_available, s.name as supplier_name
               FROM historical_inventory h1
               JOIN inventory i ON h1.nc_code = i.nc_code
               LEFT JOIN suppliers s ON i.supplier_id = s.id
               WHERE h1.date BETWEEN ? AND ?'''

    params = [start_date, end_date]

    # If suppliers are specified and not 'all'
    if suppliers and 'all' not in suppliers:
        placeholders = ', '.join('?' * len(suppliers))
        query += f" AND s.name IN ({placeholders})"
        params.extend(suppliers)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    # Processing the result
    results = [{'nc_code': row[0], 'brand_name': row[1], 'date': row[2],
                'total_available': row[3], 'supplier_name': row[4]} for row in rows]

    # Cache the results
    cache[key] = results

    return results


@inventory_bp.route('/available-dates')
def available_dates():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT date FROM historical_inventory ORDER BY date DESC")
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(dates)


@inventory_bp.route('/available-suppliers')
def available_suppliers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT name FROM suppliers ORDER BY name")
    suppliers = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(suppliers)


@inventory_bp.route('/brand-analysis', methods=['GET', 'POST'])
def brand_analysis():
    conn = get_db_connection()
    brands_df = pd.read_sql_query(
        "SELECT DISTINCT brand_name FROM inventory", conn)
    brands = brands_df['brand_name'].tolist()

    selected_brands = request.form.getlist(
        'brand[]') if request.method == 'POST' else []
    # suppliers = request.form.getlist('supplier[]')

    graphs_html = []
    if selected_brands:
        for brand in selected_brands:
            safe_brand = brand.replace("'", "''")

        # Corrected Graph 1: Brand's Inventory Over Time with Predictive Trend
        df = pd.read_sql_query(f"""
            SELECT DATE(h.date) as date, SUM(h.total_available) as total_available 
            FROM historical_inventory h
            JOIN inventory i ON h.nc_code = i.nc_code
            WHERE i.brand_name = '{safe_brand}' 
            GROUP BY DATE(h.date)
            """, conn)
        df['date_num'] = pd.to_datetime(df['date']).map(pd.Timestamp.toordinal)
        X = df[['date_num']]
        y = df['total_available']

        # Fit linear regression model
        model = LinearRegression().fit(X, y)
        df['predicted'] = model.predict(X)

        fig = px.scatter(df, x='date', y='total_available',
                         title=f'Inventory Over Time for {brand}')
        fig.add_scatter(x=df['date'], y=df['predicted'],
                        mode='lines', name='Predicted')
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)',
                          paper_bgcolor='rgba(0,0,0,0)', font_color='white')
        graphs_html.append(fig.to_html())

        # Graph 2: Average Monthly Inventory Levels
        df_monthly = pd.read_sql_query(f"""
            SELECT strftime('%Y-%m', h.date) as month, AVG(h.total_available) as avg_available
            FROM historical_inventory h
            JOIN inventory i ON h.nc_code = i.nc_code
            WHERE i.brand_name = '{safe_brand}'
            GROUP BY month
            """, conn)
        fig_monthly = px.bar(df_monthly, x='month', y='avg_available',
                             title=f'Average Monthly Inventory for {brand}')
        fig_monthly.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='white')
        graphs_html.append(fig_monthly.to_html())

        # Graph 3: Rate of Inventory Change
        df_rate = pd.read_sql_query(f"""
            SELECT h.date, (h.total_available - LAG(h.total_available) OVER (ORDER BY h.date)) as rate_change
            FROM historical_inventory h
            JOIN inventory i ON h.nc_code = i.nc_code
            WHERE i.brand_name = '{safe_brand}'
            """, conn)
        fig_rate = px.line(df_rate, x='date', y='rate_change',
                           title=f'Rate of Inventory Change for {brand}')
        fig_rate.update_layout(plot_bgcolor='rgba(0,0,0,0)',
                               paper_bgcolor='rgba(0,0,0,0)', font_color='white')
        graphs_html.append(fig_rate.to_html())

        # Graph 4: Inventory Size Distribution Over Time
        df_size = pd.read_sql_query(f"""
            SELECT h.date, i.size, SUM(h.total_available) as total_available
            FROM historical_inventory h
            JOIN inventory i ON h.nc_code = i.nc_code
            WHERE i.brand_name = '{safe_brand}'
            GROUP BY h.date, i.size
            """, conn)
        fig_size = px.bar(df_size, x='date', y='total_available',
                          color='size', title=f'Inventory Size Distribution for {brand}')
        fig_size.update_layout(plot_bgcolor='rgba(0,0,0,0)',
                               paper_bgcolor='rgba(0,0,0,0)', font_color='white')
        graphs_html.append(fig_size.to_html())

        # Graph 5: Supplier and Broker Influence on Inventory
        df_supplier_broker = pd.read_sql_query(f"""
            SELECT h.date, s.name as supplier, b.name as broker, SUM(h.total_available) as total_available
            FROM historical_inventory h
            JOIN inventory i ON h.nc_code = i.nc_code
            JOIN suppliers s ON i.supplier_id = s.id
            JOIN brokers b ON i.broker_id = b.id
            WHERE i.brand_name = '{safe_brand}'
            GROUP BY h.date, s.name, b.name
            """, conn)
        fig_supplier_broker = px.line(df_supplier_broker, x='date', y='total_available',
                                      color='supplier', title=f'Supplier and Broker Influence for {brand}')
        fig_supplier_broker.update_traces(mode='markers+lines')
        fig_supplier_broker.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='white')
        graphs_html.append(fig_supplier_broker.to_html())

    return render_template('brand_analysis.html', brands=brands, graphs_html=graphs_html)


@inventory_bp.route('/data-analysis')
def data_analysis():
    conn = get_db_connection()

    # Graph 1: Inventory Levels Over Time (Aggregated by Day)
    df = pd.read_sql_query(
        "SELECT DATE(date) as date, SUM(total_available) as sum_of_total_available FROM historical_inventory GROUP BY DATE(date)", conn)
    fig1 = px.line(df, x='date', y='sum_of_total_available', title='Aggregated Inventory Over Time',
                   labels={'date': 'Date', 'sum_of_total_available': 'Current Sum of Total Available Cases'})
    fig1.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )

    # Graph 2: Brand-wise Inventory Distribution (Top 15)
    brand_df = pd.read_sql_query(
        "SELECT brand_name, SUM(total_available) as sum_of_total_available FROM inventory GROUP BY brand_name ORDER BY sum_of_total_available DESC LIMIT 15", conn)
    fig2 = px.bar(brand_df, x='brand_name', y='sum_of_total_available',
                  title='Top 15 Brand-wise Inventory Distribution',
                  labels={'brand_name': 'Brand Name', 'sum_of_total_available': 'Current Sum of Total Available Cases'})
    fig2.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )

    # Graph 3: Inventory Size Distribution
    size_df = pd.read_sql_query(
        "SELECT size as bottle_size, COUNT(*) as count_of_size_occurrence FROM inventory GROUP BY bottle_size", conn)
    fig3 = px.bar(size_df, x='bottle_size', y='count_of_size_occurrence',
                  title='Inventory Size Distribution',
                  labels={'bottle_size': 'Size of Bottle', 'count_of_size_occurrence': 'Current Count of Occurence of Bottle Size'})
    fig3.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )

    # Graph 4: Supplier Contribution to Inventory (Top 15)
    supplier_df = pd.read_sql_query(
        "SELECT suppliers.name, SUM(inventory.total_available) as sum_of_inv_total_avail FROM inventory JOIN suppliers ON inventory.supplier_id = suppliers.id GROUP BY suppliers.name ORDER BY sum_of_inv_total_avail DESC LIMIT 15", conn)
    fig4 = px.bar(supplier_df, x='name', y='sum_of_inv_total_avail',
                  title='Current Top 15 Supplier Contribution to Inventory',
                  labels={'name': 'Supplier', 'sum_of_inv_total_avail': 'Current Sum of Total Available Cases'})
    fig4.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )

    # Graph 5: Top 15 Brands by Total Volume (ML)
    volume_query = """
    SELECT brand_name, 
           SUM(total_available * CASE 
               WHEN size LIKE '%ML' THEN CAST(REPLACE(size, 'ML', '') AS INTEGER)
               WHEN size LIKE '%L' THEN CAST(REPLACE(size, 'L', '') AS INTEGER) * 1000
               WHEN size LIKE '%.L' THEN CAST(REPLACE(size, '.L', '') AS INTEGER) * 1000
               ELSE 0
           END) as total_volume_ml
    FROM inventory
    GROUP BY brand_name
    ORDER BY total_volume_ml DESC
    LIMIT 15
    """
    volume_df = pd.read_sql_query(volume_query, conn)
    fig5 = px.bar(volume_df, x='brand_name', y='total_volume_ml', title='Top 15 Brands by Total Volume (mL)',
                  labels={'brand_name': 'Brand Name', 'total_volume_ml': 'Current Sum of Total Volume (mL)'})
    fig5.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )

    # Convert the figures to HTML
    graphs_html = [fig.to_html() for fig in [fig1, fig2, fig3, fig4, fig5]]

    return render_template('data_analysis.html', graphs_html=graphs_html)


@inventory_bp.route('/', methods=['GET', 'POST'])
def index():
    structured_results = None
    unique_dates = None

    if request.method == 'POST':
        comparison_type = request.form.get('comparisonType')
        date1 = request.form['date1']
        date2 = request.form['date2']
        suppliers = request.form.getlist('supplier[]')

        if comparison_type == 'direct':
            results = compare_inventory_data(date1, date2, suppliers)
            return render_template('results.html', results=results, date1=date1, date2=date2, comparison_type=comparison_type)

        elif comparison_type == 'range':
            results = compare_inventory_data_date_range(
                date1, date2, suppliers)
            unique_dates = sorted(set(row['date'] for row in results))
            structured_results = {}
            for row in results:
                brand = row['brand_name']
                if brand not in structured_results:
                    structured_results[brand] = {
                        'supplier_name': row['supplier_name'], 'totals': {}}
                structured_results[brand]['totals'][row['date']
                                                    ] = row['total_available']
            return render_template('results.html', results=structured_results, unique_dates=unique_dates, comparison_type=comparison_type)

    graph_dir = 'static/img/graphs/'
    graph_filenames = sorted(
        [f for f in os.listdir(graph_dir) if f.endswith('.png')],
        reverse=True  # Sort to get the most recent files first
    )
    return render_template('index.html', graph_filenames=graph_filenames)
