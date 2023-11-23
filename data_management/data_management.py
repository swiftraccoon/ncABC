import sqlite3
import pandas as pd
from dotenv import load_dotenv
import os
import requests
from datetime import datetime

# Load environment variables from .env file
load_dotenv()


def initialize_db(conn):
    """Initialize the database by creating necessary tables."""
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS suppliers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS brokers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
                        nc_code TEXT PRIMARY KEY,
                        brand_name TEXT,
                        total_available INTEGER,
                        size TEXT,
                        cases_per_pallet INTEGER,
                        supplier_id INTEGER,
                        broker_id INTEGER,
                        FOREIGN KEY (supplier_id) REFERENCES suppliers (id),
                        FOREIGN KEY (broker_id) REFERENCES brokers (id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS historical_inventory (
                        nc_code TEXT,
                        date TEXT,
                        total_available INTEGER,
                        supplier_id INTEGER,
                        PRIMARY KEY (nc_code, date),
                        FOREIGN KEY (nc_code) REFERENCES inventory (nc_code),
                        FOREIGN KEY (supplier_id) REFERENCES suppliers (id))''')

    conn.commit()


def create_db_connection(db_file):
    """Create a database connection to the SQLite database specified by db_file."""
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        print(e)
    return None


def fetch_and_save_inventory(url, backup_dir):
    """Fetch inventory data from the provided URL and save it to a CSV file."""
    response = requests.get(url)
    if response.status_code == 200:
        today = datetime.now().strftime("%Y%m%d")
        filename = f"{backup_dir}/{today}.csv"
        os.makedirs(backup_dir, exist_ok=True)
        with open(filename, 'wb') as file:
            file.write(response.content)
        return filename
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return None


def read_csv_data(file_path):
    """Read CSV data from the given file path."""
    return pd.read_csv(file_path)


def insert_unique_data(conn, table_name, data):
    """Insert unique data into the given table."""
    cursor = conn.cursor()
    for item in data:
        cursor.execute(
            f'INSERT OR IGNORE INTO {table_name} (name) VALUES (?)', (item,))
    conn.commit()


def update_inventory(conn, df):
    """Update the inventory table and move old data to historical_inventory."""
    cursor = conn.cursor()

    # Insert or update current inventory
    for _, row in df.iterrows():
        cursor.execute('''INSERT OR REPLACE INTO inventory (nc_code, brand_name, total_available, 
                          size, cases_per_pallet, supplier_id, broker_id) 
                          VALUES (?, ?, ?, ?, ?, 
                          (SELECT id FROM suppliers WHERE name = ?), 
                          (SELECT id FROM brokers WHERE name = ?))''',
                       (row['NC Code'], row['Brand Name'], row['Total Available'],
                           row['Size'], row['Cases Per Pallet'], row['Supplier'], row['Broker Name']))

    # Move old data to historical_inventory
    cursor.execute('''INSERT INTO historical_inventory (nc_code, date, total_available, supplier_id)
                      SELECT nc_code, date('now'), total_available, supplier_id FROM inventory''')

    conn.commit()


def main():
    db_file = os.getenv("DB_FILE_PATH")
    inventory_url = os.getenv("INVENTORY_URL")
    backup_dir = os.getenv("BACKUP_DIR")

    csv_file = fetch_and_save_inventory(inventory_url, backup_dir)
    if csv_file:
        conn = create_db_connection(db_file)
        if conn is not None:
            initialize_db(conn)
            df = read_csv_data(csv_file)

            # Insert unique suppliers and brokers
            insert_unique_data(conn, 'suppliers', df['Supplier'].unique())
            insert_unique_data(conn, 'brokers', df['Broker Name'].unique())

            # Update inventory
            update_inventory(conn, df)

            conn.close()
            print("Database update complete.")
        else:
            print("Error! Cannot create the database connection.")
    else:
        print("Failed to download or save inventory data.")


if __name__ == "__main__":
    main()
