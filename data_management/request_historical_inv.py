import requests
import datetime
import argparse
import sys


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Retrieve data for a date range.')
    parser.add_argument('--date_start', required=True,
                        help='Start date in YYYYMMDD format')
    parser.add_argument('--date_end', required=True,
                        help='End date in YYYYMMDD format')
    args = parser.parse_args()

    # Convert start and end dates to datetime objects
    start_date = datetime.datetime.strptime(args.date_start, '%Y%m%d')
    end_date = datetime.datetime.strptime(args.date_end, '%Y%m%d')
    print(f'Start date: {start_date.strftime("%Y%m%d")}')
    print(f'End date: {end_date.strftime("%Y%m%d")}')

    # URL and initial cookies
    url = 'https://abc2.nc.gov/StoresBoards/ExportExcel'

    # Iterate through the date range
    current_date = start_date
    print(f'Current date: {current_date.strftime("%Y%m%d")}')

    print(f'URL: {url}')
    print(f'Checking if {current_date} is >= {end_date}')
    while current_date <= end_date:
        print(f'Current date: {current_date.strftime("%Y%m%d")}')
        print(f'End date: {end_date.strftime("%Y%m%d")}')
        # Prepare the cookies for the current date
        cookies = {'BrandName': '',
                   'ReportDate': current_date.strftime('%m/%d/%Y')}
        print(f'Cookies: {cookies}')
        # Make the POST request
        response = requests.post(url, cookies=cookies)

        # Write request and response information to sys.stdout
        sys.stdout.write(
            f'Sending POST request to {url} for {current_date.strftime("%Y%m%d")}\n')
        sys.stdout.write(f'Response status code: {response.status_code}\n')
        sys.stdout.flush()  # Ensure immediate output

        # Check if the request was successful (status code 200)
        print(f'Checking if {response.status_code} == 200')
        if response.status_code == 200:
            print(f'{response.status_code} == 200')
            # Specify the file name with the current date
            file_name = current_date.strftime('%Y%m%d.csv')

            # Save the response content as a CSV file
            with open(file_name, 'wb') as file:
                file.write(response.content)

            sys.stdout.write(f'Successfully saved CSV file as {file_name}\n')
            sys.stdout.flush()  # Ensure immediate output
        else:
            sys.stderr.write(
                f'Failed to make the POST request for {current_date.strftime("%Y%m%d")}. Status code: {response.status_code}\n')
            sys.stderr.flush()  # Ensure immediate output
            break

        # Move to the next date
        print(f'Completed for {current_date}')
        current_date += datetime.timedelta(days=1)
        print(f'Moving on to {current_date}')


if __name__ == "__main__":
    main()
