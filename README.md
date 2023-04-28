# Electrify Seattle: Building Performance Data Analysis

This repo contains the data analysis and subsequent reports done by the data science team on [350 Seattle's](https://350seattle.org/) ⚡Electrify Seattle⚡ campaign during Winter-Spring 2023. 



## Repo Structure: 
- [data](data/): contains raw and intermediate data.
- [experiments](experiments/): notebooks for initial exploration. 
- [utils](utils/): contains extracted preprocessing, plotting, and other commonly-used functions. To have access to all of these utility functions, run `pip install .` in root. 



## Data Pipeline Structure
- Github repo: stores experiments and experiment results, as well as code used to update/clean data.
- Big Query: stores data in a SQL database. Reachable by API. 
- Google Sheets: displays current Big Query data in a spreadsheet, pulled in automatically. This is available for organizers who want to see the data but are not comfortable with SQL.


## Getting Up and Running With the Pipeline
- Sign up for a [Google Cloud account](https://cloud.google.com/gcp?utm_source=google&utm_medium=cpc&utm_campaign=na-US-all-en-dr-bkws-all-all-trial-p-dr-1605212&utm_content=text-ad-none-any-DEV_c-CRE_532287060476-ADGP_Desk+%7C+BKWS+-+PHR+%7C+Txt+~+Top-KWID_43700064911463909-kwd-6052401663&utm_term=KW_google+cloud-ST_google+cloud&gclid=CjwKCAiAioifBhAXEiwApzCztnlhgdVhJomjQJHXqxQRhF8QNKa6JsRQl6Rh3KrA5400sLaTGyZzjRoCaJgQAvD_BwE&gclsrc=aw.ds&hl=en)
- Ask Isaac to add you as an editor to the 350 Seattle project in Google Cloud.
- Install the [Pandas Big Query SDK](https://github.com/googleapis/python-bigquery-pandas), which allows you to access Big Query directly from Pandas. You will need to use Python3 and pip3 for this library. *Note*: this is *not* the same as the Big Query Python API.
- To authenticate, you have [two choices](https://googleapis.dev/python/pandas-gbq/latest/howto/authentication.html#id2):
    - Use Google Cloud authorization already cached on your machine
    - The first time you run a query with the library, you'll be prompted to log in on a pop up window
- You should now be able to run the code in the [API example](experiments/big_query_api_example.ipynb) successfully.
    - If you see an error about the `tdqm` library, run `pip install tdqm` and restart your iPython kernel.
- Use the Pandas Big Query library to read and write data to the Source of Truth dataset in Big Query. Be sure to log all changes in our change log. Any changes you make will be visible in the Google Sheets display of the data.
