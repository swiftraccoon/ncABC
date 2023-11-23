import matplotlib.pyplot as plt
import sqlite3
import datetime
from dotenv import load_dotenv
import os
import pandas as pd

# Load environment variables from .env file
load_dotenv()


def convert_size_to_ml(size):
    """Convert different size formats to milliliters."""
    try:
        if 'L' in size.upper():
            # Convert from liters to milliliters
            return float(size.upper().replace('L', '')) * 1000
        elif 'ML' in size.upper():
            # Already in milliliters
            return float(size.upper().replace('ML', ''))
        else:
            # Unknown format
            return 0
    except ValueError:
        # Handle cases where the conversion to float fails
        return 0


def calculate_total_ml_available(row):
    """Calculate total milliliters available for a brand."""
    size_ml = convert_size_to_ml(row['size'])
    return size_ml * row['total_available'] * row['cases_per_pallet']


def process_query_results(rows):
    for row in rows:
        row['total_ml_available'] = calculate_total_ml_available(row)
    return rows


def generate_inventory_graph(conn):
    cursor = conn.cursor()

    # Query to get data (example: total inventory over time)
    cursor.execute(
        'SELECT date, SUM(total_available) FROM historical_inventory GROUP BY date')
    data = cursor.fetchall()

    # Separate the data into two lists for plotting
    dates = [datetime.datetime.strptime(row[0], '%Y-%m-%d') for row in data]
    totals = [row[1] for row in data]

    # Generate the plot
    plt.figure(figsize=(15, 8))
    # Set the style of the plot to be suitable for dark mode
    plt.style.use('dark_background')
    plt.plot(dates, totals, marker='o')
    plt.title('Total Cases Over Time', color='white')
    plt.xlabel('Date', color='white')
    plt.ylabel('Total Case Inventory', color='white')
    plt.grid(True, color='gray')
    plt.tight_layout()

    date = datetime.datetime.now().strftime("%Y%m%d")
    # Save the plot
    plt.savefig(
        f'../web/static/img/graphs/{date}_inv_over_time.png')


def query_inventory_data(conn, limit, offset):
    cursor = conn.cursor()

    # Query to find top brands based on historical inventory levels
    top_brands_query = '''
    SELECT i.brand_name, SUM(h.total_available) as total
    FROM historical_inventory h
    JOIN inventory i ON h.nc_code = i.nc_code
    WHERE h.date BETWEEN ? AND ?
    GROUP BY i.brand_name
    ORDER BY total DESC
    LIMIT ? OFFSET ?
    '''
    start_date = '2023-10-01'
    end_date = '2023-11-22'
    # Execute the query with all four parameters
    cursor.execute(top_brands_query, (start_date, end_date, limit, offset))
    top_brands = [row[0] for row in cursor.fetchall()]

    # Prepare placeholders for SQL IN clause
    placeholders = ','.join('?' * len(top_brands))

    # Query to get historical inventory data for these brands
    historical_query = '''
    SELECT i.brand_name, h.date, h.total_available, i.cases_per_pallet, i.size
    FROM historical_inventory h
    JOIN inventory i ON h.nc_code = i.nc_code
    WHERE i.brand_name IN ({})
    ORDER BY i.brand_name, h.date
    '''.format(placeholders)

    cursor.execute(historical_query, top_brands)
    data = cursor.fetchall()

    # Calculate total_ml_available and create a DataFrame
    processed_data = []
    for row in data:
        # Assuming 'size' is the fifth column in the SELECT
        size_ml = convert_size_to_ml(row[4])
        # Assuming 'total_available' and 'cases_per_pallet' are the third and fourth columns
        total_ml_available = size_ml * row[2] * row[3]
        processed_data.append({
            'brand_name': row[0],  # Assuming 'brand_name' is the first column
            'date': row[1],  # Assuming 'date' is the second column
            'total_ml_available': total_ml_available
        })

    return pd.DataFrame(processed_data, columns=['brand_name', 'date', 'total_ml_available'])


def plot_inventory_trends(df, title, top):
    plt.figure(figsize=(15, 8))
    # Set the style of the plot to be suitable for dark mode
    plt.style.use('dark_background')
    for brand in df['brand_name'].unique():
        brand_df = df[df['brand_name'] == brand]
        plt.plot(brand_df['date'], brand_df['total'], label=brand)

    plt.title(title, color='white')
    plt.xlabel('Date', color='white')
    plt.ylabel('Total mL Available', color='white')
    plt.legend()
    plt.grid(True, color='gray')

    date = datetime.datetime.now().strftime("%Y%m%d")

    # Save the plot with the current date in the filename
    plt.savefig(
        f'../web/static/img/graphs/{date}_brand_{top}_inv_over_time.png')
    plt.close()


def main():
    db_file = os.getenv("DB_FILE_PATH")
    # Connect to the database
    conn = sqlite3.connect(db_file)

    # Call the function to generate the graph
    generate_inventory_graph(conn)

    # Get data for top 15 brands
    top_15_df = query_inventory_data(conn, 8, 0)
    plot_inventory_trends(
        top_15_df, 'Top 8 Brands - Inventory Over Time', "top8")

    # Get data for brands ranked 16-31
    next_16_df = query_inventory_data(conn, 9, 15)
    plot_inventory_trends(
        next_16_df, 'Brands 9-18 - Inventory Over Time', "top9t18")

    top_50_df = query_inventory_data(conn, 50, 0)
    plot_inventory_trends(
        top_50_df, 'Top 50 - Inventory Over Time', "top50")

    # Close the database connection
    conn.close()


if __name__ == "__main__":
    main()
