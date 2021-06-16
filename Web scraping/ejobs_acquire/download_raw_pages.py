"""Download all the pages given in an input file"""
import argparse
import csv
import sqlite3
import time
from datetime import datetime
import zlib

import requests

DATE_FORMAT = '%Y-%m-%d'

ejobs_table = (
    "CREATE TABLE IF NOT EXISTS ejobs ("
    "url TEXT PRIMARY KEY,"
    "status INTEGER,"
    "date_archived TEXT,"
    "date_downloaded TEXT,"
    "page BLOB);")


def download_pages(url_file, sqlite_file):
    """Download all urls and store the data"""
    # the second column is expected to be the URL
    URL_COL = 1
    DATE_COL = 0

    conn = sqlite3.connect(sqlite_file)

    # create table
    with conn:
        conn.execute(ejobs_table)

    with open(url_file, 'r') as f:
        csv_reader = csv.reader(f, delimiter=',', quotechar='"')
        i = 0
        cur = conn.cursor()
        for row in csv_reader:
            try:
                i += 1
                print(i, row[0])
                # check if record has been successfully downloaded
                cur.execute("SELECT status FROM ejobs WHERE url = ?", (row[URL_COL], ))
                status = cur.fetchone()

                if status and status[0] == 200:
                    continue

                print('Downloading:', row[URL_COL])
                try:
                    page = requests.get(row[URL_COL])
                    status_code = page.status_code
                    page_content = page.content
                except Exception as err:
                    status_code = 999
                    page_content = None
                    print(err)

                cur.execute("REPLACE INTO ejobs(url, status, page, date_archived, date_downloaded) VALUES (?, ?, ?, ?, ?)",
                            (row[URL_COL], status_code, zlib.compress(page_content) if page_content else None,
                             row[DATE_COL], datetime.now().strftime(DATE_FORMAT)))
                conn.commit()

                time.sleep(0.1)
            except Exception as e:
                conn.rollback()
                print(e)

    conn.close()


def cli():
    """Command line interface"""
    parser = argparse.ArgumentParser(description='Download the data raw web pages and store them in an SQLite DB.')
    parser.add_argument('infile', help='Input CSV file with two columns: date, url. No header.')
    parser.add_argument('outfile', help='Name of SQLite DB file to store the data in.')

    args = parser.parse_args()

    return args.infile, args.outfile


if __name__ == '__main__':
    infile, outfile = cli()
    download_pages(infile, outfile)
