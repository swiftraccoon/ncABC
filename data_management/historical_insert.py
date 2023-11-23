import sqlite3
import pandas as pd
import os
import glob
from datetime import datetime
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


def create_db_connection(db_path):
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(e)
    return None


def insert_historical_data(conn, df, date):
    cursor = conn.cursor()

    # Check if data for this date already exists
    cursor.execute(
        "SELECT EXISTS(SELECT 1 FROM historical_inventory WHERE date=?)", (date,))
    if cursor.fetchone()[0] == 1:
        print(f"Data for date {date} already exists. Skipping.")
        return

    # Insert data into historical_inventory table
    for _, row in df.iterrows():
        cursor.execute('''INSERT INTO historical_inventory (nc_code, date, total_available)
                          VALUES (?, ?, ?)''',
                       (row['NC Code'], date, row['Total Available']))

    conn.commit()
    print(f"Data for date {date} inserted successfully.")


def process_csv_files(folder_path, db_path):
    conn = create_db_connection(db_path)
    if conn is not None:
        # Process each CSV file in the folder
        for file_path in glob.glob(os.path.join(folder_path, '*.csv')):
            file_name = os.path.basename(file_path)
            date_str = file_name.split('.')[0]  # Extract date from filename

            try:
                date = datetime.strptime(date_str, "%Y%m%d").date()
                df = pd.read_csv(file_path)
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
