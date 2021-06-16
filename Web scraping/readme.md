# eJobs scraper utility

## Get CLI help

```
python -m ejobs_acquire.main -h
```

## Usage example
Download and parse eJobs ads from 2018 January 1 to 2021 March 31 (end date included).
Save tha urls to `urls.csv`csv file.
Raw data to `raw.sqlite` SQLite database file.
Parsed data to `parsed.sqlite` SQLite database file.
```
python -m ejobs_acquire.main 2018-01-01 2021-03-31 ./data/urls.csv ./data/raw.sqlite ./data/parsed.sqlite
```