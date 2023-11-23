#!/bin/bash

# Directory containing the files
directory="csv_bkups"

# Change to the specified directory
cd "$directory"

# Loop through all csv files with the format 'nc_revenue_MM_DD_YYYY.csv'
for file in nc_revenue_*.csv; do
    if [[ $file =~ nc_revenue_([0-9]{1,2})_([0-9]{1,2})_([0-9]{4}).csv ]]; then
        month=${BASH_REMATCH[1]}
        day=${BASH_REMATCH[2]}
        year=${BASH_REMATCH[3]}

        # Pad month and day with zero if necessary
        printf -v newname '%04d%02d%02d.csv' "$year" "$month" "$day"

        # Rename the file
        mv "$file" "$newname"
        echo "Renamed $file to $newname"
    fi
done
