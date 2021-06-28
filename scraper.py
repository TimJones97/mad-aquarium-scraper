from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import sys, csv, time, os, timeit, re, boto3, urllib.request

HEADLESS = False
total_items = 0

def csv_writer(filename):
    HEADER = ['product_name', 'image_count', 'product_text']
    targetfile = open(filename, mode='w', encoding='utf-8', newline='\n')
    writer = csv.writer(targetfile, quoting=csv.QUOTE_MINIMAL)

    writer.writerow(HEADER)

    return writer

def start_browser(headless):
    print('Starting browser\n')
    option = webdriver.ChromeOptions()

    if (HEADLESS):
        option.add_argument("--headless")

    #Do not load images to save time and bandwidth
    prefs = {"profile.managed_default_content_settings.images": 2}
    option.add_experimental_option("prefs", prefs)

    # Do not allow notifications
    # prefs = {"profile.default_content_setting_values.notifications" : 2}
    # option.add_experimental_option("prefs", prefs)
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

    # Enable user_data directory to allow for caching for faster scraping
    option.add_argument("user-data-dir=/user_data/default/")
    option.add_argument("--start-maximized")

    browser = webdriver.Chrome(options=option)
    return browser

def get_items(url, category, writer):
    item_count = 0
    global total_items
    prev_url = ''

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
            # Prevent duplicate products by comparing current url and previous url
            if url != prev_url:
                try:
                    # Visit the page 
                    browser.get(url)

                    # Hide the annoying large footer
                    try:
                        browser.execute_script("document.getElementById('fcontainer').style.display = 'none';")
                    except Exception as e:
                        pass

                    # Grab the HTML through BeautifulSoup
                    product_page = BeautifulSoup(browser.page_source, 'html.parser')

                    # Get the innerPageTmplBox which is the product info
                    item = product_page.find('div', class_='innerPageTmplBox')

                    # Initialise the string vars to false
                    product_name = product_text = ''
                    image_count  = 0

                    # Create an empty dictionary
                    product = {}

                    # Get the product name easily
                    product_name = item.find('h3').get_text()

                    # Remove any " quotation marks
                    product_name = product_name.replace('"', 'inch').replace('/', '_')

                    # Add the attribute to the dictionary
                    product['product_name'] = product_name

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

                            # Strip the product name from any symbols to prevent saving errors

                            # Give the image a easier-to-read name, replacing URL encoding
                            image_name = image_name.replace('%2B', ' ').replace('-', '')

                            # Filepath to save the images to
                            path = './product_images/' + category + '/' + product_name + '/'

                            # Create a new folder with the product name
                            try:
                                os.makedirs(path)
                            except FileExistsError:
                                pass

                            image_path = path + image_name

                            # Download found images into their respective folder
                            urllib.request.urlretrieve(image_src, image_path)

                            # Increment the image count
                            image_count += 1

                        product['image_count'] = image_count

                        # Get all of the text elements -> structure <div class="dmNewParagraph"><div></div>
                        text_divs = item.find_all('div', class_='dmNewParagraph')

                        # Find all nested divs
                        for nested_div in text_divs:
                            nested_div.find_all('div')

                            # Attempt to get all the text from each div
                            try:
                                for div in nested_div:
                                    text_temp = div.get_text()

                                    # Get the text (if available)
                                    if len(text_temp) != 0 and text_temp != None:

                                        # If the last character of the line is a colon,
                                        # this means that it is a title. Only add one
                                        # breakline
                                        if text_temp[-1] == ':': 

                                            # Append the text
                                            product_text += text_temp + '\n'
                                        else:
                                            product_text += text_temp + '\n\n'

                            # If none exist, continue execution
                            except Exception as e:
                                pass

                        # Remove the new line \n\n spacing from the last line of the text
                        product_text = product_text[:-4]
                        product['product_text'] = product_text

                    except Exception as e:
                        trace_back = sys.exc_info()[2]
                        line = trace_back.tb_lineno
                        print("Process Exception in line {}".format(line), e)
                        continue

                    writer.writerow(product.values())

                except Exception as e:
                    trace_back = sys.exc_info()[2]
                    line = trace_back.tb_lineno
                    print("Process Exception in line {}".format(line), e)
                    continue

                total_items += 1
                prev_url = url

    except Exception as e:
        trace_back = sys.exc_info()[2]
        line = trace_back.tb_lineno
        print("Process Exception in line {}".format(line), e)

    return total_items

def download_products(browser):
    current_file = 'products_list.csv'
    writer = csv_writer(current_file)

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

        item_counter = get_items(url, category, writer)

        stop = timeit.default_timer()
        total_time = stop - start
        print (item_counter, category, "stored successfully in", total_time, 'seconds')

if __name__ == '__main__':
    start = timeit.default_timer()     

    try:
        browser = start_browser(HEADLESS)
        download_products(browser)

        # If everything goes to plan:
        browser.quit()
     
    # If crashed, say why and close chromedriver process
    except Exception as e:
        browser.quit()
        print(e)
        
    stop = timeit.default_timer()
    
    total_time = stop - start
    total_time = str(round(total_time, 2))
    print('\nCompleted in', total_time, 'seconds with', total_items, 'products stored.')
