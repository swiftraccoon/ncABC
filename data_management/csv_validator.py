import os
import csv


def is_valid_format(file_path):
    """Checks if the given file matches the expected CSV format."""
    expected_header = ["NC Code", "Brand Name", "Total Available", "Size",
                       "Cases Per Pallet", "Supplier", "Supplier Allotment", "Broker Name"]

    with open(file_path, 'r', newline='') as file:
        try:
            reader = csv.reader(file)
            header = next(reader)

            # Strip whitespace and remove empty strings from header fields
            header = [h.strip() for h in header if h.strip()]

            if header != expected_header:
                print(f"Header mismatch in {file_path}: {header}")
                return False

            for row in reader:
                if not row or not row[0].strip().startswith('="'):
                    print(f"Row format mismatch in {file_path}: {row}")
                    return False
                if reader.line_num > 35:  # Check first 35 lines
                    break
        except csv.Error as e:
            print(f"CSV error in {file_path}: {e}")
            return False

    return True


def find_non_conforming_files(folder_path):
    """Finds and returns a list of non-conforming files in the given folder."""
    non_conforming_files = []
    for filename in filter(lambda f: f.endswith('.csv'), os.listdir(folder_path)):
        file_path = os.path.join(folder_path, filename)
        if not is_valid_format(file_path):
            non_conforming_files.append(filename)
    return non_conforming_files


folder_path = 'csv_bkups'  # Replace with your folder path
non_conforming_files = find_non_conforming_files(folder_path)
print("Non-conforming files:", non_conforming_files)
