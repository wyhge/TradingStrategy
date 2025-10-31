import requests
from bs4 import BeautifulSoup

def get_latest_notices(stock_code):
    # stock_code 直接用 600519，不加 .SH
    url = f"https://data.eastmoney.com/notices/stock/{stock_code}.html"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    resp = requests.get(url, headers=headers)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "lxml")

    notices = []
    for row in soup.select("div.notice_cont a"):
        title = row.get_text(strip=True)
        link = row.get("href")
        notices.append({
            "公告标题": title,
            "链接": link
        })
    return notices

print(get_latest_notices("600519"))