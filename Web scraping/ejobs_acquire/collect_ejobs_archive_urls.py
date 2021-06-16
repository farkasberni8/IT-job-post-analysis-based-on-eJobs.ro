"""Collect the URLs of all the job ads in the given period."""

import bs4
import requests
import datetime
import time
import argparse

DATE_FORMAT = '%Y-%m-%d'

yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

base_url = 'https://www.ejobs.ro/arhiva'

months_names = {1: 'Ianuarie', 2: 'Februarie', 3: 'Martie', 4: 'Aprilie', 5: 'Mai', 6: 'Iunie',
                7: 'Iulie', 8: 'August', 9: 'Septembrie', 10: 'Octombrie', 11: 'Noiembrie', 12: 'Decembrie'}


def generate_day_url(date):
    """Create the URL from date"""
    return '/'.join([base_url, str(date.year), months_names[date.month].lower(), str(date.day)])


def crawl_ejobs_archive(start_date, end_date, out_file, sleep_time=0.5):
    """
    Crawl the ejobs archive between the start and end dates.
    Save all the job ads links into the out_file.

    """

    date = start_date

    while date <= end_date:

        arch_url = generate_day_url(date)
        page_number = 1
        day_links = []

        while True:
            url = arch_url + '/Pagina_{page}.html'.format(page=page_number)
            print(url)

            page = requests.get(url)
            soup = bs4.BeautifulSoup(page.text, 'lxml')

            new_links = [a['href'] for a in soup.find_all('a') if
                         a.get('href') and (
                         # simple job link
                         a['href'].startswith('https://www.ejobs.ro/user/locuri-de-munca/')
                         or
                         # updated job link
                         a['href'].startswith('https://www.ejobs.ro/personalizat/'))]

            if not new_links:
                # there are no job links on pages above max pagination
                break

            day_links.extend(new_links)
            page_number += 1
            time.sleep(sleep_time)

        with open(out_file, 'a') as f:
            for lnk in day_links:
                f.write(','.join([date.strftime(DATE_FORMAT), lnk]))
                f.write('\n')

        date = date + datetime.timedelta(days=1)


def cli():
    """Command line interface"""
    parser = argparse.ArgumentParser(description='Collect the URL of all the job ads from the ejobs.ro archive.')
    parser.add_argument('start_date', help='Start date in format YYYY-MM-DD (e.g. 2019-01-01)')
    parser.add_argument('end_date', help='End date YYYY-MM-DD (e.g. 2019-01-01)')
    parser.add_argument('out_file', help='The name of the output csv file')

    args = parser.parse_args()
    # parse the dates
    start_date = datetime.datetime.strptime(args.start_date, DATE_FORMAT)
    end_date = datetime.datetime.strptime(args.end_date, DATE_FORMAT)

    if start_date > end_date:
        raise ValueError('Start date greater than end date.')

    if end_date > yesterday:
        print('End date exceeded yesterday. Yesterday will be used.')
        end_date = yesterday

    return start_date, end_date, args.out_file


if __name__ == "__main__":

    start_date, end_date, out_file = cli()
    crawl_ejobs_archive(start_date, end_date, out_file)
