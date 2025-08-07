import random
import time
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
from collections import defaultdict
import os
import pickle

# 配置参数
TARGET_URL = "https://ppwq7262.blogspot.com/2025/08/popcash.html"
MAX_VISITS_PER_RUN = 20
MIN_VISIT_INTERVAL = 15
MAX_VISIT_INTERVAL = 60
MIN_STAY_TIME = 3
MAX_STAY_TIME = 10
MIN_IP_REUSE_INTERVAL = 300
FORBIDDEN_PATHS = ["/search", "/share-widget"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/113.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)... Safari/605.1.15"
]

REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://www.yahoo.com/",
    "https://ppwq7262.blogspot.com/",
    "https://blogspot.com/",
    "https://www.reddit.com/"
]

PROXY_SOURCES = [
    'https://www.sslproxies.org/',
    'https://free-proxy-list.net/',
    'https://www.us-proxy.org/'
]

def create_driver_with_proxy(proxy=None):
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    if proxy:
        options.add_argument(f"--proxy-server=http://{proxy}")
    driver = uc.Chrome(options=options, version_main=139)
    return driver

def load_ip_history(filename='ip_history.pkl'):
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            return pickle.load(f)
    return defaultdict(float)

def save_ip_history(history, filename='ip_history.pkl'):
    with open(filename, 'wb') as f:
        pickle.dump(history, f)

def fetch_free_proxies():
    proxies = []
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    print("开始获取代理...")
    for source in PROXY_SOURCES:
        try:
            response = requests.get(source, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'id': 'proxylisttable'})
            if not table: continue
            rows = table.find_all('tr')[1:]
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 7:
                    ip = cols[0].text.strip()
                    port = cols[1].text.strip()
                    protocol = cols[6].text.strip().lower()
                    if 'elite' in cols[4].text.lower() and protocol == 'yes':
                        proxies.append(f"{ip}:{port}")
        except Exception: continue
    return list(set(proxies))

def validate_proxies(proxies, test_url='https://www.google.com', timeout=10):
    valid = []
    print("验证代理中...")
    for proxy in proxies:
        try:
            driver = create_driver_with_proxy(proxy)
            driver.set_page_load_timeout(timeout)
            driver.get(test_url)
            if "Google" in driver.title:
                valid.append(proxy)
                print(f"通过: {proxy}")
            driver.quit()
        except: continue
    return valid

def get_available_proxies(force_refresh=False, cache_file='valid_proxies.txt'):
    if not force_refresh and os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
        if proxies: return proxies
    proxies = fetch_free_proxies()
    valid = validate_proxies(proxies)
    with open(cache_file, 'w') as f:
        f.write('\n'.join(valid))
    return valid

def get_suitable_proxy(proxies, ip_history):
    now = time.time()
    available = []
    for proxy in proxies:
        ip = proxy.split(':')[0]
        last = ip_history.get(ip, 0)
        if now - last >= MIN_IP_REUSE_INTERVAL:
            available.append(proxy)
    if available:
        return random.choice(available)
    proxies.sort(key=lambda x: ip_history.get(x.split(':')[0], 0))
    return proxies[0] if proxies else None

def simulate_user_behavior(driver):
    try:
        height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(random.randint(2, 5)):
            pos = random.randint(0, height)
            driver.execute_script(f"window.scrollTo(0, {pos});")
            time.sleep(random.uniform(0.5, 2))
        t = random.uniform(MIN_STAY_TIME, MAX_STAY_TIME)
        print(f"停留 {t:.2f} 秒")
        time.sleep(t)
    except Exception as e:
        print(f"用户行为出错: {str(e)}")

def visit_blog(url, proxy=None):
    try:
        driver = create_driver_with_proxy(proxy)
        driver.set_page_load_timeout(30)
        for f in FORBIDDEN_PATHS:
            if f in url:
                driver.quit()
                return False, None
        referer = random.choice(REFERERS)
        print(f"访问: {url} | Referer: {referer}")
        driver.get(url)
        try:
            driver.execute_script("window.open('https://api.ipify.org?format=text', '_blank');")
            driver.switch_to.window(driver.window_handles[1])
            ip = driver.find_element("tag name", "body").text.strip()
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        except:
            ip = "未知"
        simulate_user_behavior(driver)
        driver.quit()
        return True, ip
    except Exception as e:
        print(f"访问失败: {str(e)}")
        return False, None

def main():
    print(f"目标: {TARGET_URL}")
    
    visit_count = 10  # 固定访问次数
    refresh_proxies = False  # 是否强制刷新代理
    use_local = True  # 允许使用本地IP

    ip_history = load_ip_history()
    proxies = get_available_proxies(force_refresh=refresh_proxies)

    if not proxies and not use_local:
        return

    success = 0
    start = time.time()

    for i in range(1, visit_count + 1):
        print(f"\n第 {i} 次访问")
        proxy = get_suitable_proxy(proxies, ip_history) if proxies else None
        ok, ip = visit_blog(TARGET_URL, proxy)
        if ok:
            success += 1
            if ip != "未知":
                ip_history[ip] = time.time()
        if i < visit_count:
            wait = random.uniform(MIN_VISIT_INTERVAL, MAX_VISIT_INTERVAL)
            print(f"等待 {wait:.2f} 秒...\n")
            time.sleep(wait)

    save_ip_history(ip_history)
    print(f"完成: {success}/{visit_count} | 耗时: {time.time()-start:.2f}s")


if __name__ == "__main__":
    main()
