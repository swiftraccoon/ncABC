# Define the date ranges for 2022
date_ranges=(
    "--date_start 20230101 --date_end 20230131"
    "--date_start 20220101 --date_end 20220131"
    "--date_start 20220201 --date_end 20220228"
    "--date_start 20220301 --date_end 20220331"
    "--date_start 20220401 --date_end 20220430"
    "--date_start 20220501 --date_end 20220531"
    "--date_start 20220601 --date_end 20220630"
    "--date_start 20220701 --date_end 20220731"
    "--date_start 20220801 --date_end 20220831"
    "--date_start 20220901 --date_end 20220930"
    "--date_start 20221001 --date_end 20221031"
    "--date_start 20221101 --date_end 20221130"
    "--date_start 20221201 --date_end 20221231"
    "--date_start 20210101 --date_end 20210131"
    "--date_start 20210201 --date_end 20210228"
    "--date_start 20210301 --date_end 20210331"
    "--date_start 20210401 --date_end 20210430"
    "--date_start 20210501 --date_end 20210531"
    "--date_start 20210601 --date_end 20210630"
    "--date_start 20210701 --date_end 20210731"
    "--date_start 20210801 --date_end 20210831"
    "--date_start 20210901 --date_end 20210930"
    "--date_start 20211001 --date_end 20211031"
    "--date_start 20211101 --date_end 20211130"
    "--date_start 20211201 --date_end 20211231"
)

# Loop through the date ranges
for dates in "${date_ranges[@]}"; do
    python request_historical_inv.py $dates
done
