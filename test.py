
import requests

def get_szse_announcements(stock_code):
    url = "http://www.szse.cn/api/disc/announcement/annList"
    params = {
        'pageSize': 5,
        'pageNum': 1,
        'stockCode': stock_code
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "http://www.szse.cn/"
    }

    resp = requests.get(url, params=params, headers=headers)
    try:
        data = resp.json()
        return data.get("announceList", [])
    except Exception as e:
        print("解析 JSON 出错:", e)
        print("返回原始数据:", resp.text[:300])
        return []

print(get_szse_announcements("000001"))  # 平安银行