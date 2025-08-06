from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import random
import time
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import os
import pickle

# 配置参数
TARGET_URL = "https://ppwq7262.blogspot.com/2025/08/popcash.html"
MAX_VISITS_PER_RUN = 20  # 单次运行最大访问次数
MIN_VISIT_INTERVAL = 15  # 最小访问间隔(秒)
MAX_VISIT_INTERVAL = 60  # 最大访问间隔(秒)
MIN_STAY_TIME = 3  # 页面最小停留时间(秒)
MAX_STAY_TIME = 10  # 页面最大停留时间(秒)
MIN_IP_REUSE_INTERVAL = 300  # 同一IP最小复用间隔(秒)
FORBIDDEN_PATHS = ["/search", "/share-widget"]  # 禁止访问的路径

# 主流浏览器User-Agent列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/113.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/113.0.1774.57 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
]

# 可能的Referer来源（相关博客或搜索引擎）
REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://www.yahoo.com/",
    "https://ppwq7262.blogspot.com/",
    "https://blogspot.com/",
    "https://www.reddit.com/"
]

# 免费代理网站列表
PROXY_SOURCES = [
    'https://www.sslproxies.org/',
    'https://free-proxy-list.net/',
    'https://www.us-proxy.org/'
]

def load_ip_history(filename='ip_history.pkl'):
    """加载IP使用历史记录"""
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            return pickle.load(f)
    return defaultdict(float)

def save_ip_history(history, filename='ip_history.pkl'):
    """保存IP使用历史记录"""
    with open(filename, 'wb') as f:
        pickle.dump(history, f)

def fetch_free_proxies():
    """从免费代理网站获取代理列表"""
    proxies = []
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
    print("开始从免费代理网站获取代理...")
    
    for source in PROXY_SOURCES:
        try:
            print(f"正在从 {source} 获取代理...")
            response = requests.get(source, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取表格中的代理信息
            table = soup.find('table', {'id': 'proxylisttable'})
            if not table:
                continue
                
            rows = table.find_all('tr')[1:]  # 跳过表头
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 7:
                    ip = cols[0].text.strip()
                    port = cols[1].text.strip()
                    protocol = cols[6].text.strip().lower()
                    
                    # 只收集支持https的高匿代理
                    if 'elite' in cols[4].text.lower() and protocol == 'yes':
                        proxies.append(f"{ip}:{port}")
        
        except Exception as e:
            print(f"从 {source} 获取代理失败: {str(e)}")
            continue
    
    # 去重
    proxies = list(set(proxies))
    print(f"共获取到 {len(proxies)} 个原始代理")
    return proxies

def validate_proxies(proxies, test_url='https://www.google.com', timeout=10):
    """验证代理是否可用"""
    valid_proxies = []
    
    print(f"开始验证代理，共 {len(proxies)} 个需要验证...")
    
    for proxy in proxies:
        try:
            # 配置Chrome选项
            chrome_options = Options()
            chrome_options.add_argument(f'--proxy-server=http://{proxy}')
            chrome_options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')
            chrome_options.add_argument('--headless')  # 无头模式，不显示浏览器窗口
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            
            # 尝试连接
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(timeout)
            
            start_time = time.time()
            driver.get(test_url)
            response_time = time.time() - start_time
            
            # 如果成功加载页面
            if "Google" in driver.title:
                valid_proxies.append((proxy, response_time))
                print(f"代理 {proxy} 验证通过，响应时间: {response_time:.2f}秒")
            
            driver.quit()
        
        except Exception:
            # 代理不可用，静默失败
            continue
    
    # 按响应时间排序，保留最快的代理
    valid_proxies.sort(key=lambda x: x[1])
    # 只返回代理IP:端口部分
    valid_proxies = [p[0] for p in valid_proxies]
    
    print(f"验证完成，共得到 {len(valid_proxies)} 个可用代理")
    return valid_proxies

def get_available_proxies(force_refresh=False, cache_file='valid_proxies.txt'):
    """获取可用代理，优先使用缓存"""
    # 尝试从缓存加载
    if not force_refresh and os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                proxies = [line.strip() for line in f if line.strip()]
            if proxies:
                print(f"从缓存加载 {len(proxies)} 个可用代理")
                return proxies
        except Exception as e:
            print(f"加载代理缓存失败: {str(e)}")
    
    # 获取并验证新代理
    raw_proxies = fetch_free_proxies()
    if not raw_proxies:
        print("无法获取任何原始代理")
        return []
    
    valid_proxies = validate_proxies(raw_proxies)
    
    # 保存到缓存
    if valid_proxies:
        with open(cache_file, 'w') as f:
            f.write('\n'.join(valid_proxies))
        print(f"已将可用代理保存到 {cache_file}")
    
    return valid_proxies

def get_suitable_proxy(proxies, ip_history):
    """获取合适的代理，考虑IP复用间隔"""
    current_time = time.time()
    
    # 过滤掉不符合复用间隔的代理
    available_proxies = []
    for proxy in proxies:
        ip = proxy.split(':')[0]
        last_used = ip_history.get(ip, 0)
        
        if current_time - last_used >= MIN_IP_REUSE_INTERVAL:
            available_proxies.append(proxy)
    
    if not available_proxies:
        print(f"没有符合IP复用间隔({MIN_IP_REUSE_INTERVAL}秒)的代理，将使用最早使用的代理")
        # 按最后使用时间排序，返回最早使用的
        proxies_with_time = [(p, ip_history.get(p.split(':')[0], 0)) for p in proxies]
        proxies_with_time.sort(key=lambda x: x[1])
        return proxies_with_time[0][0] if proxies_with_time else None
    
    # 随机选择一个可用代理
    return random.choice(available_proxies)

def simulate_user_behavior(driver):
    """模拟真实用户行为"""
    try:
        # 随机滚动页面
        scroll_height = driver.execute_script("return document.body.scrollHeight")
        scroll_positions = [random.randint(0, scroll_height) for _ in range(random.randint(2, 5))]
        
        for pos in scroll_positions:
            driver.execute_script(f"window.scrollTo(0, {pos});")
            time.sleep(random.uniform(0.5, 2))  # 滚动后停留
        
        # 随机停留时间
        stay_time = random.uniform(MIN_STAY_TIME, MAX_STAY_TIME)
        print(f"页面停留 {stay_time:.2f} 秒")
        time.sleep(stay_time)
        
        return True
    except Exception as e:
        print(f"模拟用户行为时出错: {str(e)}")
        return False

def visit_blog(url, proxy=None):
    """访问博客页面"""
    try:
        # 在visit_blog函数的chrome_options配置中添加
        chrome_options.binary_location = "/usr/bin/chromium-browser"
        chrome_options.add_argument("--headless=new")  # Ubuntu服务器版无界面时需启用
        # 配置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')  # 避免被检测为自动化工具
        chrome_options.add_argument('--start-maximized')  # 最大化窗口
        
        # 添加代理
        if proxy:
            chrome_options.add_argument(f'--proxy-server=http://{proxy}')
        
        # 添加Referer
        referer = random.choice(REFERERS)
        chrome_options.add_argument(f'referer={referer}')
        
        # 初始化浏览器
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        
        # 检查是否是禁止访问的路径
        for forbidden in FORBIDDEN_PATHS:
            if forbidden in url:
                print(f"禁止访问路径: {url}")
                driver.quit()
                return False, None
        
        # 访问目标URL
        print(f"正在访问: {url} | Referer: {referer}")
        driver.get(url)
        
        # 获取当前IP（通过访问IP查询网站）
        try:
            driver.execute_script("window.open('https://api.ipify.org?format=text', '_blank');")
            driver.switch_to.window(driver.window_handles[1])
            ip_address = driver.find_element('tag name', 'body').text.strip()
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            print(f"当前IP: {ip_address}")
        except Exception:
            ip_address = "未知"
        
        # 模拟用户行为
        simulate_user_behavior(driver)
        
        # 关闭浏览器
        driver.quit()
        return True, ip_address
        
    except Exception as e:
        print(f"访问失败: {str(e)}")
        if 'driver' in locals():
            driver.quit()
        return False, None

def main():
    print("=== 博客自动访问脚本 ===")
    print(f"目标URL: {TARGET_URL}")
    
    # 获取访问次数（不超过最大限制）
    try:
        visit_count = int(input(f"请输入访问次数(1-{MAX_VISITS_PER_RUN}): "))
        visit_count = min(max(visit_count, 1), MAX_VISITS_PER_RUN)
    except:
        visit_count = 5
        print(f"使用默认访问次数: {visit_count}")
    
    # 加载IP历史记录
    ip_history = load_ip_history()
    
    # 获取代理
    refresh_proxies = input("是否强制刷新代理列表? (y/n): ").lower() == 'y'
    proxies = get_available_proxies(force_refresh=refresh_proxies)
    
    if not proxies:
        print("警告: 未获取到任何可用代理，将使用本地IP访问")
        use_local = input("是否继续使用本地IP访问? (y/n): ").lower() == 'y'
        if not use_local:
            print("程序退出")
            return
    
    # 开始访问
    print(f"\n开始访问，共 {visit_count} 次...\n")
    success_count = 0
    current_time = time.time()
    
    for i in range(1, visit_count + 1):
        print(f"第 {i}/{visit_count} 次访问:")
        
        # 获取合适的代理
        proxy = get_suitable_proxy(proxies, ip_history) if proxies else None
        
        # 访问博客
        success, ip_address = visit_blog(TARGET_URL, proxy)
        
        if success:
            success_count += 1
            # 更新IP历史记录
            if ip_address != "未知":
                ip_history[ip_address] = time.time()
        
        # 随机延迟，最后一次不延迟
        if i < visit_count:
            delay = random.uniform(MIN_VISIT_INTERVAL, MAX_VISIT_INTERVAL)
            print(f"等待 {delay:.2f} 秒后进行下一次访问...\n")
            time.sleep(delay)
    
    # 保存IP历史记录
    save_ip_history(ip_history)
    
    # 统计结果
    total_time = time.time() - current_time
    print(f"\n访问完成 | 总次数: {visit_count} | 成功次数: {success_count} | 成功率: {success_count/visit_count*100:.2f}%")
    print(f"总耗时: {total_time:.2f}秒")

if __name__ == "__main__":
    # 确保使用前安装所需库
    # pip install selenium beautifulsoup4
    # 同时需要下载对应版本的ChromeDriver并添加到系统PATH
    main()
    
