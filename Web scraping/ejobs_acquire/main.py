"""
The main module to rerun the entire data acquisition from one entry point.
NOTE: it only works with archived eJobs.ro job ads.
"""
from . import collect_ejobs_archive_urls, download_raw_pages, parse_raw_pages

import argparse
import datetime

DATE_FORMAT = '%Y-%m-%d'


def cli():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description='Run the data collection and job ad parsing from the ejobs.ro archive.')
    parser.add_argument('start_date', help='Start date in format YYYY-MM-DD (e.g. 2019-01-01)')
    parser.add_argument('end_date', help='End date YYYY-MM-DD (e.g. 2019-01-01)')
    parser.add_argument('url_file', help='The name of the output csv file')
    parser.add_argument('raw_sqlite', help='The name of the SQLite file for storing the raw download.')
    parser.add_argument('parsed_sqlite', help='The name of SQLite file storing the parsed data.')

    args = parser.parse_args()
    # parse the dates
    start_date = datetime.datetime.strptime(args.start_date, DATE_FORMAT)
    end_date = datetime.datetime.strptime(args.end_date, DATE_FORMAT)

    if start_date > end_date:
        raise ValueError('Start date greater than end date.')

    if end_date > collect_ejobs_archive_urls.yesterday:
        print('End date exceeded yesterday. Yesterday will be used.')
        end_date = collect_ejobs_archive_urls.yesterday

    return start_date, end_date, args.url_file, args.raw_sqlite, args.parsed_sqlite


if __name__ == '__main__':
    start_date, end_date, url_file, raw_sqlite, parsed_sqlite = cli()
    print('Collecting URLs...')
    collect_ejobs_archive_urls.crawl_ejobs_archive(start_date, end_date, url_file)
    print('Downloading raw data...')
    download_raw_pages.download_pages(url_file, raw_sqlite)
    print('Parsing raw data...')
    parse_raw_pages.main(raw_sqlite, parsed_sqlite)
