import requests
import redis
from bs4 import BeautifulSoup

r = redis.Redis(host="redis", port=6379, decode_responses=True)

def fetch_proxies():
    url = "https://free.kuaidaili.com/free/inha/1/"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", attrs={"class": "table"})
    for row in table.tbody.find_all("tr"):
        ip = row.find_all("td")[0].text
        port = row.find_all("td")[1].text
        proxy = f"http://{ip}:{port}"
        if validate_proxy(proxy):
            r.rpush("proxies", proxy)

def validate_proxy(proxy):
    try:
        resp = requests.get("http://httpbin.org/ip", proxies={"http": proxy, "https": proxy}, timeout=3)
        return resp.status_code == 200
    except:
        return False

if __name__ == "__main__":
    fetch_proxies()