from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import redis
import random
import time

r = redis.Redis(host="redis", port=6379, decode_responses=True)
TARGET_URL = "https://example.com"

def get_proxy():
    proxies = r.lrange("proxies", 0, -1)
    if not proxies:
        return None
    return random.choice(proxies)

def visit():
    proxy = get_proxy()
    if not proxy:
        print("No proxy available")
        return
    chrome_options = Options()
    chrome_options.add_argument(f"--proxy-server={proxy}")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(TARGET_URL)
        time.sleep(5)
        print(driver.title)
    finally:
        driver.quit()

if __name__ == "__main__":
    visit()