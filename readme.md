# Early Warning Wisenews Scraper readme
last updated: October 23, 2020

---

## I. Contents
This repository contains all the files for sending Hong Kong news articles on Wisenews to CSRP colleagues. The class WisenewsScraper also contains a routine to save scraped articles to a local MongoDB collection.

This is a standalone version of Wisenews scraper.  Also check repository `openup-triage-server` for an integrated solution for Django.

---

## II. Pip requirements
+ a working python virtual environment - follow Python or Conda documentation to set up one if you haven't already done so.
+ `Selenium` >= 3.141.0
+ `openpyxl` >= 2.6.3
+ `pymongo` >= 3.8.0
+ `jupyter-core` >=4.5 and associated packages if running Jupyter Notebook file

---

## III. Other system requirements
+ `Google Chrome` - https://www.google.com/chrome/ - for selenium controller
+ `ChromeDriver` - https://chromedriver.chromium.org/ - select a version to match `Google Chrome`
+ `MongoDB` >= 4.0

---

## IV. Suggested modifications before running the code
1. Open `python wisenews.py` with a text editor - recommended ones are `vim`, `sublime`, or `notepad++`
2. modify the global variable `WISENEWS_NEWS_SECTIONS` to select a subset of news articles to download from Wisenews
3. modify tuples in the enum `Keywords` to tailor keywords for searching news articles
4. change the chromedriver path accordingly

---

## V. Usage
1. If this is your first time running this scraper, create `.env` file as follows:

```bash
cat env_template > .env # this will create a new environment file called .env using env_template as base
```
Open and edit your `.env` credentials accordingly:

```python
# Wisenews Login
HKU_LOGIN='HKU_PID_HERE'            # your HKU login.  Must be a real one.
HKU_PASSWORD='HKU_PASSWORD_HERE'    # your HKU password.  Must be a real one.
SENDER='SENDER_NAME_HERE'           # i.e. Byron
FROM_EMAIL='SENDER EMAIL HERE'      # i.e. byron@csrp.hku.hk
TO_EMAIL='RECEPIENT EMAIL HERE'     # i.e. staff@csrp.hku.hk
```

2. Source into the python virtual environment.
3. Either: a) In `jupyter notebook` run the notebook file `Wisenews.ipynb` or b) enter `python wisenews.py` in bash.

Full details on usage: see the `main` function of `wisenews.py` and the Jupyter notebook `Wisenews.ipynb` 