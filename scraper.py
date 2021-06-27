from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import sys, time, os, timeit, re, boto3, urllib.request

HEADLESS = False
total_items = 0

def start_browser(headless):
    print('Starting browser\n')
    option = webdriver.ChromeOptions()

    if (HEADLESS):
        option.add_argument("--headless")

    #Do not load images to save time and bandwidth
    prefs = {"profile.managed_default_content_settings.images": 2}
    option.add_experimental_option("prefs", prefs)

    # Do not allow notifications
    prefs = {"profile.default_content_setting_values.notifications" : 2}
    option.add_experimental_option("prefs", prefs)
    option.add_argument("--disable-dev-shm-usage") #overcome limited resource problems
    option.add_argument("--no-sandbox") #Bypass OS security model
    option.add_argument("--disable-extensions")
    option.add_argument("--disable-infobars")
    option.add_argument("--disable-gpu")
    option.add_argument("--disable-software-rasterizer")
    option.add_argument("--disable-crash-reporter")
    option.add_argument("--disable-in-process-stack-traces")
    option.add_argument("--ignore-certificate-errors")
    option.add_argument("--disable-logging")
    option.add_argument("--log-level=3")
    option.add_argument("--output=/dev/null")
    option.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36")
    option.add_argument('--host-resolver-rules=MAP au11-tracker.inside-graph.com 127.0.0.1')
    option.add_argument("--window-size=1920,1080")
    option.add_argument("user-data-dir=/user_data/default/")
    option.add_argument("--start-maximized")

    browser = webdriver.Chrome(options=option)
    return browser

def generate_products_query(title, title_condensed, link, image, retailer, product_category):
    # Fill this in later
    product_insert_query = "INSERT INTO products (title) VALUES \
    ('" + title + "', '" + other_attribute + "', '" + other_attribute + "', '" + other_attribute + "', '" + other_attribute + "');"

    return product_insert_query

def get_items(url, category):
    item_count = 0
    global total_items
    # cur = serv.cursor()

    browser.get(url)
    print ('Getting products in the', category, 'category\n')

    # Grab the HTML through BeautifulSoup
    category_page = BeautifulSoup(browser.page_source, 'html.parser')
    try:
        # Get all of the heading elements (subcategory titles)
        heading_elements = category_page.find('div', class_='innerPageTmplBox').find_all('h2')
        headings = []
        product_urls = []

        # Get the categories on the current page
        for heading in heading_elements:
            headings.append(heading.get_text())

        # Get each of the anchor tags on the page
        anchor_elems = category_page.select("a[link_type^=popup]")\

        # Extract the href which is the URL minus the domain
        # and append to array
        for anchor in anchor_elems:
            item_url = anchor['href']
            item_url = 'https://www.madaquariums.com.au' + item_url
            product_urls.append(item_url)

        # For each product link
        for url in product_urls:  
            try:

                # Visit the page 
                browser.get(url)

                # Grab the HTML through BeautifulSoup
                product_page = BeautifulSoup(browser.page_source, 'html.parser')

                # Get the innerPageTmplBox which is the product info
                item = product_page.find('div', class_='innerPageTmplBox')

                # Initialise the string vars to false
                description_text = tube_depth = size = lengths = ideal_for = features = False

                # Get the product name easily
                product_name = item.find('h3').get_text()

                # Replacing any " quotation marks with spaces
                product_name = product_name.replace('"', '')

                # Attempt to get the other attributes
                try:

                    # Get all img elements
                    images = item.find_all('img')

                    # Iterate through found images
                    for image in images:

                        # Get the src attribute of the image (the URL)
                        image_src = image['src']

                        # Split the URL by each '/' and get the last string from the 
                        # string array, this will be the image filename
                        image_name = image_src.split('/')[-1]

                        # Give the image a easier-to-read name, replacing URL encoding
                        image_name = product_name + ' ' + image_name.replace('%2B', ' ')

                        # Filepath to save the images to
                        path = './product_images/' + product_name + '/'

                        # Create a new folder with the product name
                        try:
                            os.makedirs(path)    
                        except FileExistsError:
                            pass

                        image_path = path + image_name

                        # Download found images into their respective folder
                        urllib.request.urlretrieve(image_src, image_path)

                    # Get all of the font elements
                    font_items = item.find_all('font')

                    # The description title is hidden in a font element
                    for font_item in font_items:

                        # Get the description (if available)
                        if font_item.get_text() == 'Description:':
                            description_parent = font_item.parent.parent.parent
                            description_text = description_parent.find_all('div')[2].get_text()

                            # If the description text is not nested within 3 divs, it will only be nested in 2
                            if len(description_text) == 0:
                                description_parent = font_item.parent.parent
                                description_text = description_parent.find_all('div')[2].get_text()

                        # Get the 'Tube Depth' list (if available)
                        if 'Tube Depth:' in font_item.get_text():

                            # Convert tube_depth from bool to str
                            tube_depth = ''

                            # Iterate through the parent elements to get the desired div
                            tube_depth_parent = font_item.parent.parent

                            # Get all the li elements which are the lengths
                            tube_depth_elems = tube_depth_parent.find_all('div')[5].find('ul', class_='innerList').find_all('li')

                            # Append the 'Tube Depth' results into a single str
                            for elem in tube_depth_elems:
                                tube_depth += (elem.get_text() + ', ')

                            # Remove the last appended comma and space from the string
                            tube_depth = tube_depth[:-2]

                        # Get the size (if available)
                        if 'Size' in font_item.get_text():

                            # Convert size from bool to str
                            size = ''

                            # Iterate through the parent elements to get the desired div
                            size_parent = font_item.parent.parent.parent.parent

                            # Get all the li elements which are the sizes
                            size_elems = size_parent.find('ul', class_='innerList').find_all('li')

                            # Append the lengths into a single str
                            for elem in size_elems:
                                size += (elem.get_text() + ', ')

                            # Remove the last appended comma and space from the string
                            size = size[:-2]

                        # Get the lengths (if available)
                        if 'Length' in font_item.get_text():

                            # Convert lengths from bool to str
                            lengths = ''

                            # Iterate through the parent elements to get the desired div
                            length_parent = font_item.parent.parent.parent.parent

                            # Get all the li elements which are the lengths
                            length_elems = length_parent.find('ul', class_='innerList').find_all('li')

                            # Append the lengths into a single str
                            for elem in length_elems:
                                lengths += (elem.get_text() + ', ')

                            # Remove the last appended comma and space from the string
                            lengths = lengths[:-2]

                        # Get the 'Ideal for' text (if available)
                        if 'Ideal' in font_item.get_text():

                            # Convert ideal_for from bool to str
                            ideal_for = ''

                            # Iterate through the parent elements to get the desired div
                            ideal_for_parent = font_item.parent.parent

                            # Get all the li elements which are the lengths
                            ideal_for_elems = ideal_for_parent.find_all('div')[4].find('ul', class_='innerList').find_all('li')

                            # If the description text is not nested within 3 divs, it will only be nested in 2
                            if len(ideal_for_elems) == 0:
                                description_text = ideal_for_parent.find_all('div')[5].get_text()

                            # Append the 'Ideal For' reasons into a single str
                            for elem in ideal_for_elems:
                                ideal_for += (elem.get_text() + ', ')

                            # Remove the last appended comma and space from the string
                            ideal_for = ideal_for[:-2]

                        # Get the 'Features' text (if available)
                        if 'Features' in font_item.get_text():

                            # Convert ideal_for from bool to str
                            features = ''

                            # Iterate through the parent elements to get the desired div
                            features_parent = font_item.parent.parent.parent

                            # Get all the li elements which are the lengths
                            features_elems = features_parent.find_all('div')[5].find('ul', class_='innerList').find_all('li')

                            # Append the 'Ideal For' reasons into a single str
                            for elem in features_elems:
                                features += (elem.get_text() + ', ')

                            # Remove the last appended comma and space from the string
                            features = features[:-2]

                except Exception as e:
                    print(e)

                # Added for debug
                print('Product name:', product_name)
                print('Product image to download:', image_src)
                print('Product description:', description_text)
                print('Product lengths:', lengths)
                print('Ideal for:', ideal_for)
                print('Tube depth:', tube_depth)
                print('Features:', features)
                print('Size:', size)

            except Exception as e:
                trace_back = sys.exc_info()[2]
                line = trace_back.tb_lineno
                print("Process Exception in line {}".format(line), e)
                continue

            total_items += 1
    except Exception as e:
        trace_back = sys.exc_info()[2]
        line = trace_back.tb_lineno
        print("Process Exception in line {}".format(line), e)

    return total_items

def store_items(serv, p_link, p_image, p_title, p_price, p_cat, retailer):
    item_count = 0
    link = p_link 
    image = p_image
    title = p_title
    price = p_price
    product_category = p_cat
    # cur = serv.cursor()

    # Replace each quotation mark and forward slash in the title with a space
    title = title.replace('"', ' ').replace('/', ' ');
    # Include letters, numbers, fullstop, plus symbol and dash in the product title
    title = re.sub(r"[^+-.a-zA-Z0-9 ]+", '', title.strip())
    price = re.sub(r"[^.0-9]+", '', price.strip())
    # If debug flag set
    if(DEBUG):
        # Print the variables
        print(link)
        print(image)
        print(title)
        print(price)
    # Store the data
    else:
        # Remove dashes for title_condensed 
        title_condensed = title.replace(" ", "").replace("-", "").lower()
        products_query = generate_products_query(title, title_condensed, link, image, retailer, product_category)
        cur.execute(products_query)
        price_query = generate_prices_query(title_condensed, price, retailer)
        cur.execute(price_query)
        # print(price_query)
        serv.commit()

# def download_products(serv, browser):
def download_products(browser):
    start = timeit.default_timer()
    item_counter = 0
    category = ''

    # URLs for scraping
    urls = [
            'https://www.madaquariums.com.au/shop/accessories',
            'https://www.madaquariums.com.au/shop/filters-pumps',
            'https://www.madaquariums.com.au/shop/heaters',
            'https://www.madaquariums.com.au/shop/food',
            'https://www.madaquariums.com.au/shop/testkits',
            'https://www.madaquariums.com.au/shop/chemicals',
            'https://www.madaquariums.com.au/shop/medication',
            'https://www.madaquariums.com.au/shop/plants-gravel-and-soil',
            'https://www.madaquariums.com.au/shop/lighting',
            'https://www.madaquariums.com.au/shop/ornaments'
            ]

    for index, url in enumerate(urls):
        start = timeit.default_timer()

        # Split the URL by each '/' and get the last string from the 
        # string array, this will be the category page indicator as seen above.
        # Also remove - dashes and replace with spaces
        category = url.split('/')[-1].replace('-', ' ')

        item_counter = get_items(url, category)

        stop = timeit.default_timer()
        total_time = stop - start
        print (item_counter, category, " stored successfully in", total_time, 'seconds')

def db_conn():
    #Connect to Amazon RDS DB, can be replaced by output to CSV using CSV writer library
    conn = psycopg2.connect(database="postgres", user="", password="", host="", port="5432")
    print ("\nConnected to database")
    return conn

def db_create(conn):
    cur = conn.cursor()

    # Add in product table creation code here
    print ('\nSuccessfully created new product table')

    conn.commit()
    return conn

if __name__ == '__main__':
    start = timeit.default_timer()     

    try:
        # db_serv = db_conn()
        # download_products(db_serv, browser)
        browser = start_browser(HEADLESS)
        download_products(browser)

        # If everything goes to plan:
        browser.quit()
        # db_serv.close()
     
    # If crashed, say why and close chromedriver process
    except Exception as e:
        browser.quit()
        # db_serv.close()
        print(e)
        
    stop = timeit.default_timer()
    
    total_time = stop - start
    total_time = str(round(total_time, 2))
    print('\nCompleted in', total_time, 'seconds with', total_items, 'products stored.')
