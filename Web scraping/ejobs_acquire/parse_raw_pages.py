"""Module for parsing raw html pages for extracting structured data"""
import argparse
import os
import re
import sqlite3
import sys
import zlib

import traceback

from bs4 import BeautifulSoup

MONTH_NUMBER = {'Ian': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'Mai': '05', 'Iun': '06',
                'Iul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'}


def text(tag):
    """
    Get the soup tag's text if the tag exists.
    """
    if tag is not None:
        return tag.text.strip()


def remove_text(s, substr):
    if not s:
        return s

    return re.sub(substr + r'\s+', '', s)


# dates_re = re.compile(r'(Publicat|Reactualizat)([\w\s]*)[^|]*(\|.*(Expiră)(.*))?')

def extract_dates(s):
    """Extract the posting, update and expiration dates of the job."""
    if s is None:
        return

    dates_re = re.compile(
        r'Publicat(?P<date_posted>[\w\s]*)(\|\s*Reactualizat(?P<date_updated>[\w\s]*))?(\|\s*Expiră(?P<date_expired>[\w\s]*))?')

    res = {
        "date_posted": None,
        "date_updated": None,
        "date_expired": None
    }

    md = dates_re.match(s)
    if md:
        groups = md.groupdict()
        for k in res:
            res[k] = translate_date(groups[k].strip()) if groups[k] else None

    return res


def translate_date(date_str):
    """Translate the date from dd <month abreviation> yyyy fromat into isoformat yyyy-mm-dd"""
    date_str = date_str.strip()
    if len(date_str) != 11:
        raise ValueError('Unexpected date format')

    iso_date = '-'.join([date_str[7:11], MONTH_NUMBER[date_str[3:6]], date_str[0:2]])
    return iso_date


post_re = re.compile(r'(\d+)\s+post(uri)?', re.IGNORECASE)


def extract_number_positions(s):
    """Extract the number ot open position as integer or None."""
    if s is None:
        return None
    n = None
    m = post_re.search(s)
    if m:
        try:
            n = int(m.group(1))
        except ValueError:
            n = None

    return n


job_table = (
    "CREATE TABLE IF NOT EXISTS job ("
    "id INTEGER PRIMARY KEY,"
    "url TEXT,"
    "title TEXT,"
    "company TEXT,"
    "candidate TEXT,"
    "description TEXT,"
    "company_description TEXT,"
    "company_url TEXT,"
    "company_id INTEGER,"
    "date_posted TEXT,"
    "date_expired TEXT,"
    "date_updated TEXT,"
    "positions INTEGER,"
    "other_info TEXT,"
    "native_id INTEGER,"
    "date_archived TEXT,"
    "date_downloaded TEXT,"
    "download_status INTEGER"
    ");")

content_table_template = (
    "CREATE TABLE IF NOT EXISTS {table_name} ("
    "id INTEGER PRIMARY KEY,"
    "job_id INTEGER,"
    "value TEXT,"
    "FOREIGN KEY (job_id) REFERENCES job (id)"
    ");"
)

content_table_names = [
    "study", "city", "department", "industry", "type", "language", "level"
]

content_id_dict = {
    "study": "studii",
    "city": "oras",
    "department": "departament",
    "type": "jobType",
    "language": "limba",
    "industry": "industrie",
    "level": "levels"
}

tables = [
    job_table
]

tables.extend([content_table_template.format(table_name=t) for t in content_table_names])
tables.extend(
    [content_table_template.format(table_name='salary'),
     content_table_template.format(table_name='license')]
)

sql_insert_job = ("INSERT INTO job ("
                  "url, "
                  "title, "
                  "company, "
                  "candidate, "
                  "description, "
                  "company_description, "
                  "company_url, "
                  "company_id, "
                  "date_posted, "
                  "date_expired, "
                  "date_updated, "
                  "positions, "
                  "other_info, "
                  "native_id, "
                  "date_archived, "
                  "date_downloaded, "
                  "download_status"
                  ")"
                  " VALUES ("
                  ":url, "
                  ":title, "
                  ":company, "
                  ":candidate, "
                  ":description, "
                  ":company_description, "
                  ":company_url, "
                  ":company_id, "
                  ":date_posted, "
                  ":date_expired, "
                  ":date_updated, "
                  ":positions, "
                  ":other_info, "
                  ":native_id, "
                  ":date_archived, "
                  ":date_downloaded, "
                  ":download_status"
                  ");")

sql_get_id = "SELECT last_insert_rowid();"

sql_insert_content_template = ("INSERT INTO {table_name} ("
                               "job_id,"
                               "value) "
                               " VALUES ("
                               ":job_id,"
                               ":value);")

def job_record_factory():
    """Return an empty job dict."""
    return {
        "url": None,
        "title": None,
        "company": None,
        "candidate": None,
        "description": None,
        "company_description": None,
        "company_url": None,
        "company_id": None,
        "date_posted": None,
        "date_expired": None,
        "date_updated": None,
        "positions": None,
        "other_info": None,
        "native_id": None,
        "date_archived": None,
        "date_downloaded": None,
        "download_status": None
    }


def get_job_basic_data(soup):
    """Extract the basic data about the job."""

    job = job_record_factory()
    # job ad main header: title, dates, positions
    job_header = soup.find('div', class_='jobad-hero-main')

    if job_header:
        # get the posting, update and exp. dates
        dates = extract_dates(text(job_header.find('div', class_='jobad-dates')))

        if dates:
            for k in dates:
                if dates[k]:
                    job[k] = dates[k]

        if not job["date_posted"]:
            job["date_posted"] = text(job_header.find('span', itemprop='datePosted'))

        # get the title
        job['title'] = text(job_header.find('h1', class_='jobad-title'))

        facts = job_header.find('div', class_='jobad-facts').find_all('span')

        # extract n position and other info
        job['other_info'] = ','.join((text(k) for k in facts if k.text))
        job['positions'] = extract_number_positions(job['other_info'])

        company_href = job_header.find('div', class_='jobad-company-hero').find('a')
        job['company'] = text(company_href)

        if not job['company']:
            job['company'] = text(job_header.find('div', class_='jobad-company-hero'))

        if company_href:
            job['company_url'] = company_href.get('href')
            job['company_id'] = get_native_id(job['company_url'])

    # job detalii
    job_content = soup.find('section', class_='jobad-content')

    if job_content:
        job_content_blocks = job_content.find_all('div', class_='jobad-content-block')

        for k in job_content_blocks:
            title = text(k.find('h2'))
            if title == 'Candidatul ideal':
                job['candidate'] = remove_text(text(k), 'Candidatul ideal')
            elif title == 'Descrierea jobului':
                job['description'] = remove_text(text(k), 'Descrierea jobului')
            elif title == 'Descrierea companiei':
                job['company_description'] = remove_text(text(k), 'Descrierea companiei')
            else:
                print('New content:', title)
    else:
        job_image = soup.find('div', id='customJobImageContainer')
        if job_image:
            job_image = job_image.find('img')

        if job_image:
            job['description'] = 'IMG: ' + job_image['alt']

    return job


def get_content(soup, content_id):
    contents = []
    cont = soup.find('div', id=f'content-{content_id}')
    if cont:
        for d in cont.find_all('a', class_="Criteria__Link"):
            contents.append(text(d))

    return contents


def get_salary_license(soup):
    sl = {
        'salary': [],
        'license': []
    }

    ct = soup.find_all('h3', class_="Criteria__Title")
    for k in ct:
        if text(k) == "Salariu net":
            sl['salary'].extend([text(s) for s in k.find_next_siblings('span')])
        elif text(k) == "Permis conducere":
            sl['license'].extend([text(s) for s in k.find_next_siblings('span')])

    return sl


def cli():
    """Command line interface"""
    parser = argparse.ArgumentParser(description='Parse the raw web pages from tha input SQLite DB write the structured'
                                                 ' data into the output SQLite DB.')
    parser.add_argument('infile', help='Input SQLite DB with the raw download.')
    parser.add_argument('outfile', help='Name of SQLite DB file to store output data.')

    args = parser.parse_args()

    return args.infile, args.outfile


def get_native_id(url):
    """Get the integer part from the end of the url."""
    nid = url.split('/')[-1]
    try:
        nid = int(nid)
    except ValueError:
        nid = None

    return nid


def main(infile, outfile):
    """Do the parsing. """

    processed_conn = sqlite3.connect(outfile)
    pcur = processed_conn.cursor()

    # create all necessary tables
    with processed_conn:
        for t in tables:
            print(t)
            processed_conn.execute(t)

    raw_conn = sqlite3.connect(infile)
    cur = raw_conn.cursor()
    cur.execute("SELECT url, page, status, date_archived, date_downloaded FROM ejobs")
    i = 0
    for r in cur:
        i += 1
        if i % 100 == 0:
            print(i)

        try:
            job = job_record_factory()

            job['url'] = r[0]
            job['native_id'] = get_native_id(r[0])
            job['date_archived'] = r[3]
            job['date_downloaded'] = r[4]
            job['download_status'] = r[2]

            if not r[1]:
                # there is no page contetnt
                with processed_conn:
                    processed_conn.execute(sql_insert_job, job)
                continue

            page_content = zlib.decompress(r[1])
            soup = BeautifulSoup(page_content, 'lxml')
            # parse
            parsed_job = get_job_basic_data(soup)
            # merge the parsed job data into the job dict
            for k in parsed_job:
                if parsed_job[k]:
                    job[k] = parsed_job[k]

            salary_license = get_salary_license(soup)

            content = dict()
            for content_id in content_id_dict:
                content[content_id] = get_content(soup, content_id_dict[content_id])

            # write
            with processed_conn:
                processed_conn.execute(sql_insert_job, job)
                job_id = processed_conn.execute(sql_get_id).fetchone()[0]

                for content_id in content_id_dict:
                    for value in content[content_id]:
                        processed_conn.execute(sql_insert_content_template.format(table_name=content_id),
                                               {'job_id': job_id, 'value': value})

                for value in salary_license['salary']:
                    processed_conn.execute(sql_insert_content_template.format(table_name='salary'),
                                           {'job_id': job_id, 'value': value})

                for value in salary_license['license']:
                    processed_conn.execute(sql_insert_content_template.format(table_name='license'),
                                           {'job_id': job_id, 'value': value})

        except Exception as e:
            print(r[0])
            print(e)
            traceback.print_exc(file=sys.stdout)

    cur.close()
    raw_conn.close()

    processed_conn.close()


if __name__ == '__main__':
    infile, outfile = cli()
    if os.path.exists(outfile):
        raise FileExistsError(f'{outfile} exists, do not overwrite.')
    main(infile, outfile)
