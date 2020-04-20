# Openup Wisenews Scraper readme
last updated: April 20, 2020

---

## I. Contents
This repository contains all the files for sending Hong Kong news articles on Wisenews to CSRP colleagues. 
The class WisenewsScraper also contains a routine to save scraped articles to a local MongoDB collection.

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
1. Source into the python virtual environment.
2. Either: a) In `jupyter notebook` run the notebook file `Wisenews.ipynb` or b) enter `python wisenews.py` in bash.

Full details on usage in the main function of `wisenews.py` and the Jupyter notebook `Wisenews.ipynb` 