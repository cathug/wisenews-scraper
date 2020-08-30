# filename: wisenews.py
# Author: Byron Chiang (CSRP)
# Last Updated: July 20, 2020
#
# This script is a stand-alone version of the scraper in the 
# OpenUp Kitchen Server I wrote a while back.  It contains all the necessary 
# classes to download/scrape data from Wisenews and export results to MongoDB


import json, re, time, random, datetime
import sys, logging, traceback
import pytz, enum, os, logging

from pymongo import MongoClient 
from pymongo.errors import DuplicateKeyError
from decouple import config

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
# from selenium.webdriver.support.select import Select
from selenium.common.exceptions import TimeoutException

from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE


################################################################################
# Globals
################################################################################

DRIVER_WAIT = 60 # set wait to 60 seconds

# HK_TIME = pytz.timezone('Asia/Hong_Kong') # this uses Royal Observatory Def +7:36:41 from GMT
HK_TIME = pytz.timezone('Etc/GMT+8') # use this instead

# location of the chromedriver
# a copy can be downloaded from https://chromedriver.chromium.org/
# make sure downloaded driver version is compatible with existing Google Chrome version 
CHROMEDRIVER_PATH = os.path.expanduser(
    '~/Downloads/chromedriver_linux64/chromedriver')


# URLs
HKU_LIBRARY_LOGIN_URL = 'https://lib.hku.hk/index.html'
WISENEWS_URL = 'http://libwisenews.wisers.net.eproxy.lib.hku.hk/?gid=HKU&user=ipaccess&pwd=ipaccess'


# Add News sections here
WISENEWS_NEWS_SECTIONS = [
    '港聞', 
    '香港新聞',
    '要聞',
    '突發',
]


# logger setup
logging.basicConfig(
    level=logging.INFO,
    # filename=os.path.join(LOG_PATH, 'blob_download.log'),
    format='%(asctime)s - %(pathname)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)




class WisenewsDateRanges(enum.IntEnum):
    '''
        Date ranges enum to control the Wisenews date dropdown menu
    '''

    THREE_DAYS  = 2      
    WEEK        = 3
    YEAR_2017   = 11
    YEAR_2018   = 10
    YEAR_2019   = 9
    YEAR_2020   = 8

class Keywords(enum.Enum):
    '''
        Enum of keywords
    '''

    HELIUM =    ('helium_news', '(雪種 or 石油氣 or 笠頭 or 包頭 or 膠袋 or 氣袋 or 氮氣 or 毒氣 or 氫氣 or 吸氣 or 氣體 or 氣罐 or 氦氣 or 氣瓶 or 氣樽 or 氣罐) and (自殺 or 亡 or 命危)')
    CSRP =      ('csrp_news', '防止自殺研究中心 or 葉兆輝')
    SUICIDE =   ('suicide_news', '自殺')

    def __init__(self, database_collection, terms):
        self.database_collection = database_collection
        self.terms = terms

#-------------------------------------------------------------------------------

class Database:
    '''
        MongoDB Class
    '''

    def __init__(self, db_name, host='localhost', port=27017):
        # database related variables
        self.__client = MongoClient(
            host=host, 
            port=port,
        )

        self.__db = self.__client[db_name]

    #---------------------------------------------------------------------------

    def upsert_to_mongo(self, collection_name, document, pk):
        '''
            Function to insert data into the database if entry never existed,
            or update entry if it already exists

            param: document - a JSON-structured document and Python dict
        '''
        self.__db[collection_name].replace_one({pk : document[pk]},
            document, upsert=True)

    #---------------------------------------------------------------------------

    def insert_to_mongo(self, collection_name, document):
        '''
            Function to insert data into the database
            param: document - a JSON-structured document and Python dict
        '''
        self.__db[collection_name].insert_one(document)

    #---------------------------------------------------------------------------

    def insert_many_to_mongo(self, collection_name, documents):
        '''
            Function to insert data into the database
            param: documents - list of JSON-structured documents and Python dicts
        '''
        self.__db[collection_name].insert_many(documents)

    #---------------------------------------------------------------------------

    def create_index(self, collection_name, pk):
        '''
            Function to create index for the collection
            precondition: The collection's pk must be unique
        '''
        self.__db[collection_name].create_index(pk, unique=True)

    #---------------------------------------------------------------------------

    def count(self, collection_name):
        '''
            Function to count number of documents in the collection
        '''
        self.__db[collection_name].count_documents({})

    #---------------------------------------------------------------------------

    def __del__(self):
        '''
            Destructor - deallocate resources
        '''
        if self.__client:
            self.__client.close()

#-------------------------------------------------------------------------------

class WiseNewsScraper:
    '''
        Wisenews scraper class
    '''

    # HKU login credentials
    hku_login = config('HKU_LOGIN')
    hku_password = config('HKU_PASSWORD')


    # change the sender name, sender email, and recepient email accordingly
    sender_name = config('SENDER')
    sender_email = config('FROM_EMAIL')
    recepient_email = config('TO_EMAIL')

    
    def __init__(self):
        options = webdriver.ChromeOptions()
#         options.add_argument('--headless')
        options.add_argument('--incognito')
        options.add_argument('--disable-gpu')
        self.driver = webdriver.Chrome(
            executable_path=CHROMEDRIVER_PATH,
            options=options)

        self.main_handle = None
        self.login_handle = None
        self.view_popup = None

        self.database = Database('wisenews') # database to store collections

        logging.info('Initializing WisenewsScraper.')

    #---------------------------------------------------------------------------

    @staticmethod
    def strip_illegal_characters(x):
        '''
            Use this function to strip illegal characters
        '''
        return ILLEGAL_CHARACTERS_RE.sub('', x)

    #---------------------------------------------------------------------------

    def login_hku_library(self):
        '''
            Function to login to HKU library
            and set up EZProxy connection
        '''
        try:
            self.main_handle = self.driver.current_window_handle

            self.driver.get(HKU_LIBRARY_LOGIN_URL)
            wait = WebDriverWait(self.driver, DRIVER_WAIT)
            
            try:
                # close the popup (special notice added since November)
                wait.until(EC.element_to_be_clickable((
                    By.XPATH, '//*[@id="popup_this"]/span') ) ).click()

                # time.sleep(5)

            except TimeoutException:
                exc_type, exc_value, exc_tb = sys.exc_info()
                trace = traceback.format_exception(exc_type, exc_value, exc_tb)
                logging.info(trace)
                logging.info('No popup exists.')
        
        
            # click on login link
            wait.until(EC.title_contains('HKU Libraries') )
            wait.until(EC.element_to_be_clickable((
                By.XPATH, '//*[@class="button green"]') ) ).click()

            # switch to sign frame
            while True:
                time.sleep(10)
                if self.driver.window_handles[-1] != self.main_handle:
                    self.login_handle = self.driver.window_handles[-1]
                    break

            self.driver.switch_to.window(self.login_handle)

            # send login credentials
            wait = WebDriverWait(self.driver, DRIVER_WAIT)
            wait.until(EC.title_contains('HKUL Authentication') )
            wait.until(EC.visibility_of_element_located(
                (By.NAME,'userid') ) ).send_keys(self.hku_login)
            password = wait.until(EC.visibility_of_element_located(
                (By.NAME,'password') ) ).send_keys(self.hku_password)
            password = wait.until(EC.visibility_of_element_located(
                (By.XPATH,'/html/body/main/div/form/div/div/div[3]/button[1]') ) ).click()


            logging.info('Logged in to HKU Library.')

        except TimeoutException:
            exc_type, exc_value, exc_tb = sys.exc_info()
            trace = traceback.format_exception(exc_type, exc_value, exc_tb)
            logging.error(trace)
            sys.exit(f'Unable to log in to HKU with provided credentials.')

    #---------------------------------------------------------------------------

    def get_wisenews_portal(self):
        '''
            Function to go to WiseNews Information Portal
        '''
        
        try:
            self.driver.switch_to.window(self.main_handle)
            self.driver.get(WISENEWS_URL)

            wait = WebDriverWait(self.driver, DRIVER_WAIT)
            wait.until(EC.title_contains('WiseNews') )
            wait.until(EC.frame_to_be_available_and_switch_to_it('header') )
            wait.until(EC.presence_of_element_located(
                (By.LINK_TEXT, 'Wisers Information Portal') ) ).click()
            wait.until(EC.title_contains('Wisers Information Portal') )

            logging.info('Accessed WiseNews Portal.')

        except TimeoutException:
            exc_type, exc_value, exc_tb = sys.exc_info()
            trace = traceback.format_exception(exc_type, exc_value, exc_tb)
            logging.error(trace)
            sys.exit(f'Unable to access Wisenews Portal.')


    #---------------------------------------------------------------------------

    def search_local_news(self, *,
                          date_range=WisenewsDateRanges.THREE_DAYS,
                          keywords=Keywords.SUICIDE.terms,
                          news_section=WISENEWS_NEWS_SECTIONS):
        '''
            function to fill in parameters in search form
            Use this function to search for HK News
        '''

        try:
            wait = WebDriverWait(self.driver, DRIVER_WAIT)
            wait.until(EC.frame_to_be_available_and_switch_to_it('ws5-content') )
            
            # wait 5 seconds.  sometimes driver misses checks
            time.sleep(5)

            try:
                # close the Coronavirus Social Listening Platform popup
                wait.until(EC.visibility_of_element_located(
                    (By.XPATH, '//*[@id="popup_alert_layer"]/div[3]/a') ) ).click()

            except TimeoutException:
                exc_type, exc_value, exc_tb = sys.exc_info()
                trace = traceback.format_exception(exc_type, exc_value, exc_tb)
                logging.info(trace)
                logging.info('No popup exists.')


            
            # uncheck all regions, then set region to Hong Kong only
            wait.until(EC.visibility_of_element_located(
                (By.XPATH, '//*[@id="regionSelectAll"]') ) ).click()
            wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="hk"]') ) ).click()

            # search section
            if news_section is not None:
                wait.until(EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="ShowSection"]') ) ).send_keys(
                        ','.join(news_section) )

            # Download everything within selected daterange
            date_range_dropdown = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="DateRangePeriod"]') ) )
            for i in range(date_range):
                date_range_dropdown.send_keys(Keys.ARROW_DOWN)
            # select = Select(self.driver.find_element_by_xpath(
            #     '//select[@id="DateRangePeriod"]') )
            # select.select_by_value('last-week')

            # add search term
            wait.until(EC.element_to_be_clickable((
                By.XPATH, '//*[@id="searchTxt"]') ) ).send_keys(keywords, Keys.ENTER)


            logging.info('Set Search Parameters.')

        except TimeoutException:
            exc_type, exc_value, exc_tb = sys.exc_info()
            trace = traceback.format_exception(exc_type, exc_value, exc_tb)
            logging.error(trace)
            sys.exit(f'Unable to send search parameters to Wisenews Portal.')

    #---------------------------------------------------------------------------

    def update_search_local_news(self, *,
                                 date_range=WisenewsDateRanges.THREE_DAYS,
                                 keywords=Keywords.SUICIDE.terms,
                                 news_section=WISENEWS_NEWS_SECTIONS):
        '''
            function to update parameters in search form
            Use this function to update search parameters
            assuming searching the date range and region remain the same
        '''

        self.driver.switch_to.window(self.main_handle)

        try:
            wait = WebDriverWait(self.driver, DRIVER_WAIT)
            wait.until(EC.frame_to_be_available_and_switch_to_it('ws5-content') )
            wait.until(EC.frame_to_be_available_and_switch_to_it('result-list') )
         
            # wait 5 seconds.  sometimes driver misses checks
            time.sleep(5)
            wait.until(EC.visibility_of_element_located(
                (By.XPATH, '//*[@id="edit_search"]') ) ).click()


            # reset news section
            wait.until(EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="ShowSection"]') ) ).clear()

            # search section if specified
            if news_section is not None:
                wait.until(EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="ShowSection"]') ) ).send_keys(
                        ','.join(news_section) )


            # clear field and update search term
            wait.until(EC.element_to_be_clickable((
                By.XPATH, '//*[@id="searchTxt"]') ) ).clear()
            wait.until(EC.element_to_be_clickable((
                By.XPATH, '//*[@id="searchTxt"]') ) ).send_keys(keywords, Keys.ENTER)


            logging.info('Updated Search Parameters.')

        except TimeoutException:
            exc_type, exc_value, exc_tb = sys.exc_info()
            trace = traceback.format_exception(exc_type, exc_value, exc_tb)
            logging.error(trace)
            sys.exit(f'Unable to update search parameters on Wisenews Portal.')

    #---------------------------------------------------------------------------

    def scrape_local_news(self):
        '''
            function to scrape all news articles
        '''

        try:
            # click on view button
            wait = WebDriverWait(self.driver, DRIVER_WAIT)
            wait.until(
                EC.frame_to_be_available_and_switch_to_it('result-list') )
            wait.until(EC.visibility_of_element_located(
                (By.XPATH, '//*[@id="Imageview"]') ) ).click()
            
            # Poll when view popup window appears
            # then click button to view all articles
            wait = WebDriverWait(self.driver, DRIVER_WAIT)
            wait.until(EC.number_of_windows_to_be(3) )
            self.view_popup = self.driver.window_handles[-1]


            self.driver.switch_to.window(self.view_popup)
            wait = WebDriverWait(self.driver, DRIVER_WAIT)
            wait.until(EC.visibility_of_element_located(
                (By.XPATH, '//*[@id="ToolForm"]/table/tbody/tr[3]/td/input') ) ).click()


            # Poll if a new article popup is created
            # if yes, go to new popup and break loop
            while True:
                time.sleep(10)
                if self.driver.window_handles[-1] != self.view_popup:
                    self.view_popup = self.driver.window_handles[-1]
                    time.sleep(5)
                    self.driver.switch_to.window(self.view_popup)
                    break

            logging.info('Scraping complete.')

        except TimeoutException:
            exc_type, exc_value, exc_tb = sys.exc_info()
            trace = traceback.format_exception(exc_type, exc_value, exc_tb)
            logging.error(trace)
            sys.exit('Unable to scarpe news. Aborting')

    #---------------------------------------------------------------------------
    
    def email_news(self, *, email_title='Suicide News'):
        '''
            function to email all news articles to the recepient
        '''

        try:
            # click on view button
            wait = WebDriverWait(self.driver, DRIVER_WAIT)

            try:
                wait.until(
                    EC.frame_to_be_available_and_switch_to_it('result-list') )
            except TimeoutException:
                exc_type, exc_value, exc_tb = sys.exc_info()
                trace = traceback.format_exception(exc_type, exc_value, exc_tb)
                logging.info(trace)
                logging.info('Switching to parent frame and retrying')
                wait.until(EC.frame_to_be_available_and_switch_to_it('ws5-content') )
                wait.until(EC.frame_to_be_available_and_switch_to_it('result-list') )

            wait.until(EC.visibility_of_element_located(
                (By.XPATH, '//*[@id="Imageemail"]') ) ).click()
            
            # Poll when view popup window appears
            # then click button to view all articles
            wait = WebDriverWait(self.driver, DRIVER_WAIT)
            wait.until(EC.number_of_windows_to_be(3) )
            self.view_popup = self.driver.window_handles[-1]

            self.driver.switch_to.window(self.view_popup)
            wait = WebDriverWait(self.driver, DRIVER_WAIT)
            wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="ToolForm"]/table[1]/tbody/tr[6]/td[2]/input') ) ).send_keys(
#                 (By.XPATH, '//*[@name="sender-name"]') ) ).send_keys(
                    self.sender_name)
            wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="sender-address-id"]/td[2]/table/tbody/tr/td[1]/input') ) ).send_keys(
#                 (By.XPATH, '//*[@name="sender-address"]') ) ).send_keys(
                    self.sender_email)
            wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="email-addr"]') ) ).send_keys(
                    self.recepient_email)
            wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="ToolForm"]/table[1]/tbody/tr[9]/td[2]/input') ) ).send_keys(
#                 (By.XPATH, '//*[@name="subject"]') ) ).send_keys(
                    email_title)
            wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="emailContent"]/input') ) ).click()
            
            # wait until Javascript alert popup appears
            wait.until(EC.alert_is_present() )
            self.driver.switch_to.alert.accept()
            
            # wait until popup disappears
            time.sleep(10)
            self.view_popup = None

            logging.info('Sending complete.')

        except TimeoutException:
            exc_type, exc_value, exc_tb = sys.exc_info()
            trace = traceback.format_exception(exc_type, exc_value, exc_tb)
            logging.error(trace)
            sys.exit('Unable to send news. Aborting')
    
    #---------------------------------------------------------------------------

    def load_scrapes_into_database(self, collection,
        news_section=WISENEWS_NEWS_SECTIONS):
        '''
            Function to load entries into MongoDB
        '''

        try:
            wait = WebDriverWait(self.driver, DRIVER_WAIT)
            wait.until(EC.presence_of_all_elements_located((By.XPATH, 
                '//*[@class="bluebold"]') ) )
            wait.until(EC.presence_of_all_elements_located((By.XPATH, 
                '//*[@class="content"]') ) )
            wait.until(EC.presence_of_all_elements_located((By.XPATH, 
                '//*[@id="content_source"]/a') ) )
            wait.until(EC.presence_of_all_elements_located((By.XPATH, 
                '//*[@id="content_details"]') ) )
            
        except TimeoutException:
            exc_type, exc_value, exc_tb = sys.exc_info()
            trace = traceback.format_exception(exc_type, exc_value, exc_tb)
            logging.error(trace)
            sys.exit()

        # extract text and remove invalid unicode characters
        headings = self.driver.find_elements_by_xpath('//*[@class="bluebold"]')
        headings = [WiseNewsScraper.strip_illegal_characters(x.text) 
            for x in headings]

        # extract new content
        contents = self.driver.find_elements_by_xpath(
            '//*[@class="content"]')
        contents = [WiseNewsScraper.strip_illegal_characters(x.text) 
            for x in contents]

        # extract sources
        sources = self.driver.find_elements_by_xpath(
            '//*[@id="content_source"]/a')
        sources = [x.text for x in sources]

        # extract page numbers
        pages = self.driver.find_elements_by_xpath(
            '//*[@id="content_details"]')
        # odd entries in pages are page_details
        # even entries are unique Wisenews document ids
        page_details = [x.text for i, x in enumerate(pages) if i%2==0 ]
        document_ids = [x.text.split(': ')[-1]
            for i, x in enumerate(pages) if i%2!=0 ]

        # extract date
        date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
        page_pattern = re.compile(r'^[A-Z]{1}\d{2}\b')
        
        # create json list
        articles = []
        for source, heading, content, page_detail, document_id, in zip(
            sources, headings, contents, page_details, document_ids):
                
            article = {}
            section = []

            page_detail = (re.sub(r'\s+', '', page_detail) ).split('|')   
                
            while len(page_detail):
                item = page_detail.pop()
                if date_pattern.fullmatch(item): # if it's an ISO date
                    date = item.split('-')
                    date = datetime.datetime(
                        int(date[0]), int(date[1]), int(date[-1]), 0, 0, 0,
                        tzinfo=HK_TIME)
                        
                if page_pattern.fullmatch(item): # if contains page number
                    page = item
                else:
                    page = None
                    
                if item in news_section:
                    section.append(item)
                    
                if page_detail==[]:
                    sections="/".join(section)
                
            article['document_id'] = document_id
            article['heading'] = heading
            article['meta_data'] = {
                'source': source,
                'pub_date': date,
                'section': sections,
                'page': page,
            }

            article['content'] = content
                
                
            articles.append(article)


        self.database.create_index(collection, 'document_id')
        

        # not a big list - just insert one by one to simplify logic
        for a in articles:
            try:
                self.database.insert_to_mongo(collection, a)

            except DuplicateKeyError:
                logging.info('Insertion Skipped. Record already exists in Database.')
                pass

            except TimeoutException:
                exc_type, exc_value, exc_tb = sys.exc_info()
                trace = traceback.format_exception(exc_type, exc_value, exc_tb)
                logging.error(trace)
                sys.exit()



        logging.info('Scrapes loaded into Database.')

    #---------------------------------------------------------------------------

    def teardown(self):

        '''
            Function to deallocate all resources
            This includes signing out and closing all opened resources 
        '''

        # close popup
        if self.view_popup:
            self.driver.switch_to.window(self.view_popup)
            # self.driver.close()

        # logout and close the wisenews window
        if self.main_handle:
            self.driver.switch_to.window(self.main_handle)

            # logout using send_keys since click() won't work
            self.driver.find_element_by_link_text('Logout').send_keys(Keys.ENTER)
            logging.info('Log out of Wisenews')

        if self.login_handle:
            self.driver.switch_to.window(self.login_handle)

            # get the logout modal
            wait = WebDriverWait(self.driver, DRIVER_WAIT)
            wait.until(EC.element_to_be_clickable((By.XPATH, 
                '//*[@class="menu-arrow"]') ) ).click()
            wait.until(EC.element_to_be_clickable((By.XPATH, 
                '//*[@id="signOutButton"]') ) ).click()
            
            # self.driver.close()

        if self.driver:
            self.driver.quit()

        logging.info('Logged out successfully.')
