import sqlite3
import pandas as pd
import os
import glob
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def convert_date_format(date_str):
    # Assuming date_str is in the format 'YYYYMMDD'
    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"


def create_db_connection(db_path):
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(e)
    return None


def get_supplier_id(conn, supplier_name):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM suppliers WHERE name = ?", (supplier_name,))
    result = cursor.fetchone()
    return result[0] if result else None


def insert_historical_data(conn, df, date):
    cursor = conn.cursor()
    # print('DataFrame columns:', df.columns)

    # Add 'date' and 'supplier_id' columns to the DataFrame
    df['date'] = date
    df['supplier_id'] = df['Supplier'].apply(
        lambda x: get_supplier_id(conn, x))

    # Remove any unnecessary columns like 'Unnamed: 8'
    df = df.drop(columns=[col for col in df.columns if 'Unnamed:' in col])

    # Rename columns to match expected names
    df = df.rename(columns={'NC Code': 'nc_code',
                   'Total Available': 'total_available'})

    # Drop duplicates based on 'nc_code' and 'date'
    df = df.drop_duplicates(subset=['nc_code', 'date'])

    # Insert data into historical_inventory table
    for _, row in df.iterrows():
        # Check if record already exists
        cursor.execute(
            "SELECT 1 FROM historical_inventory WHERE nc_code=? AND date=?", (row['nc_code'], date))
        if not cursor.fetchone():
            print(f"Inserting data for {row['nc_code'], {date}}...")
            cursor.execute('''INSERT INTO historical_inventory (nc_code, date, total_available, supplier_id) VALUES (?, ?, ?, ?)''',
                           (row['nc_code'], date, row['total_available'], row['supplier_id']))
    conn.commit()
    # print(f"Data for date {date} inserted successfully.")


def process_csv_files(folder_path, db_path):
    conn = create_db_connection(db_path)
    if conn is not None:
        # Process each CSV file in the folder
        for file_path in glob.glob(os.path.join(folder_path, '*.csv')):
            print(f'Reading CSV file: {file_path}')
            file_name = os.path.basename(file_path)
            date_str = file_name.split('.')[0]  # Extract date from filename
            formatted_date = convert_date_format(
                date_str)  # Convert date format

            try:
                date = datetime.strptime(formatted_date, "%Y-%m-%d").date()
                df = pd.read_csv(file_path)
                # print(f'DataFrame head after reading CSV: \n{df.head()}')
                insert_historical_data(conn, df, date)
            except ValueError:
                print(f"Invalid filename format: {file_name}")

        conn.close()


if __name__ == "__main__":
    db_file = os.getenv("DB_FILE_PATH")
    backup_dir = os.getenv("BACKUP_DIR")
    # folder_path = input("Enter the folder path containing CSV files: ")
    # db_path = input("Enter the path to your SQLite database file: ")
    process_csv_files(backup_dir, db_file)
