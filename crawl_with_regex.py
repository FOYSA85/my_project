import re
import requests
import sys
import logging
import sqlite3
from html import unescape

# Establish database connection
con = sqlite3.connect("crawl_books.db")
cur = con.cursor()

# Create the table if it does not exist
cur.execute("""
CREATE TABLE IF NOT EXISTS books_details (
    Name TEXT, 
    Category TEXT, 
    UPC TEXT, 
    URL TEXT, 
    ImageURL TEXT, 
    Price REAL, 
    Availability TEXT, 
    Description TEXT
)
""")

def get_category_list(content):
    """হোম পেজের কন্টেন্ট থেকে ক্যাটেগরির লিস্ট ও তাদের URL নিয়ে আসে"""
    return category_pat.findall(content)

def get_book_list(content):
    """বইয়ের ক্যাটেগরি পেজের কন্টেন্ট থেকে বইয়ের নাম ও URL নিয়ে আসে"""
    content = content.replace("\n", " ")
    return book_list_pat.findall(content)

def get_product_details(content):
    """একটি প্রোডাক্ট পেজের কন্টেন্ট নিয়ে বইয়ের বিস্তারিত তথ্য (UPC, দাম, ছবি, স্টক, বিবরণ) বের করে"""
    image_base = "http://books.toscrape.com/"
    img_url = ""
    description = ""
    upc = ""
    price = ""
    availability = ""

    # Extract image URL
    result = img_pat.findall(content)
    if len(result) == 0:
        logging.warning("Image url not found!")
    else:
        img_url = result[0].replace("../../", "")
        img_url = image_base + img_url

    # Extract description
    result = desc_pat.findall(content)
    if len(result) == 0:
        logging.warning("Description not found!")
    else:
        description = unescape(result[0])

    # Extract UPC
    result = upc_pat.findall(content)
    if len(result) == 0:
        logging.warning("UPC not found!")
    else:
        upc = result[0]

    # Extract price
    result = price_pat.findall(content)
    if len(result) == 0:
        logging.warning("Price not found!")
    else:
        price = result[0]

    # Extract availability
    result = avail_pat.findall(content)
    if len(result) == 0:
        logging.warning("Availability not found!")
    else:
        availability = result[0]

    return upc, price, img_url, availability, description

def get_page_content(url):
    """একটি URL থেকে পেজের কন্টেন্ট নিয়ে আসে"""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
        return ""

def get_next_page(url, content):
    """বইয়ের তালিকার পেজের কন্টেন্ট থেকে পরবর্তী পেজের URL নিয়ে আসে"""
    result = next_page_pat.findall(content)
    if len(result) == 0:
        return None
    i = url.rfind("/")
    return url[0:i+1] + result[0]

def scrape_book_info(book_info, category_name):
    """একটি বইয়ের বিস্তারিত তথ্য নিয়ে CSV ফাইলে সংরক্ষণ করে"""
    book_url, book_name = book_info
    book_name = unescape(book_name)
    book_dict = {"Name": book_name, "Category": category_name}

    book_url = book_url.replace("../../../", "")
    book_url = "https://books.toscrape.com/catalogue/" + book_url

    book_dict["URL"] = book_url

    print(f"Scraping book: {book_name}")
    logging.info(f"Scraping: {book_url}")

    content = get_page_content(book_url)
    content = content.replace("\n", " ")

    upc, price, image_url, availability, desc = get_product_details(content)
    book_dict["UPC"] = upc
    book_dict["Price"] = price
    book_dict["ImageURL"] = image_url
    book_dict["Availability"] = availability
    book_dict["Description"] = desc

    # Insert book data into the database
    try:
        cur.execute("INSERT INTO books_details VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (book_dict["Name"], book_dict["Category"], book_dict["UPC"], book_dict["URL"],
                     book_dict["ImageURL"], book_dict["Price"], book_dict["Availability"], book_dict["Description"]))
        con.commit()
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")

def crawl_category(category_name, category_url):
    """একটি নির্দিষ্ট ক্যাটেগরির সমস্ত বই ক্রল করে এবং তাদের তথ্য সংগ্রহ করে"""
    while True:
        content = get_page_content(category_url)
        if not content:
            logging.error(f"Failed to retrieve content for category: {category_name}")
            break

        book_list = get_book_list(content)
        for book in book_list:
            scrape_book_info(book, category_name)
        
        next_page = get_next_page(category_url, content)
        if next_page is None:
            break
        category_url = next_page

def crawl_website():
    """পুরো ওয়েবসাইট ক্রল করে বইয়ের তথ্য সংগ্রহ করে CSV ফাইলে সংরক্ষণ করে"""
    url = "http://books.toscrape.com/index.html"
    host_name = "books.toscrape.com"
    content = get_page_content(url)
    if not content:
        logging.critical(f"Got empty content from {url}")
        sys.exit(1)

    category_list = get_category_list(content)
    for category in category_list:
        category_url, category_name = category
        category_url = "http://" + host_name + "/" + category_url
        crawl_category(category_name, category_url)

if __name__ == "__main__":
    # Compile regular expression patterns
    category_pat = re.compile(r'<li>\s*<a href="(catalogue/category/books/.*?)">\s*([\w\s&]+)\s*<', re.M | re.DOTALL)
    next_page_pat = re.compile(r'<li class="next"><a href="(.*?)">next</a></li>')
    book_list_pat = re.compile(r'<h3><a href="(.*?)" title="(.*?)">')
    img_pat = re.compile(r'<div class="item active">\s*<img src="(.*?)"', re.DOTALL)
    desc_pat = re.compile(r'<div id="product_description" class="sub-header">.*?<p>(.*?)</p>', re.DOTALL)
    upc_pat = re.compile(r'<th>UPC</th>\s*<td>(.*?)</td>', re.DOTALL)
    price_pat = re.compile(r'<th>Price \(incl. tax\)</th>\s*<td>\D*([\d.]+)</td>', re.DOTALL)
    avail_pat = re.compile(r'<th>Availability</th>\s*<td>(.*?)</td>', re.DOTALL)

    # Set up logging
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename="bookstore_crawler.log", level=logging.DEBUG)

    # Start crawling
    crawl_website()

    # Close the database connection
    con.close()
