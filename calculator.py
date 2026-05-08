from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ChromeDriver path (optional if it's already in PATH)
# service = Service('/path/to/chromedriver')

options = Options()
options.add_argument("--start-maximized")

# ব্রাউজার চালু করা
driver = webdriver.Chrome(options=options)

try:
    # পেজে যাওয়া
    driver.get('https://www.rokomari.com/book/178414/paradoxical-sajid-2')

    # অপেক্ষা করা যতক্ষণ না রেটিং এলিমেন্ট পাওয়া যায়
    wait = WebDriverWait(driver, 60)
    rating_element = wait.until(EC.presence_of_element_located(
        (By.CLASS_NAME, 'detailsReviewHeader_ratingSummary___aFy_')
    ))

    # রেটিং প্রিন্ট করা (যদি ভিতরে কোনো লেখা থাকে)
    print("Rating Text:", rating_element.text)

finally:
    # সবশেষে ব্রাউজার বন্ধ করা
    driver.quit()
