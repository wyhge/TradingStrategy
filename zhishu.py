import requests

# 指数代码和名称映射
index_codes = {
    "上证指数": "1.000001",
    "深证成指": "0.399001",
    "创业板指": "0.399006",
    "沪深300": "1.000300"
}

def get_index_data():
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    results = {}
    for name, code in index_codes.items():
        resp = requests.get(url, params={
            'secid': code,
            'fields': 'f43,f44,f45,f46,f60,f57,f169,f170'
        })
        data = resp.json()['data']
        results[name] = {
            "最新价": data['f43'] / 100,  # 最新点位
            "涨跌幅": round((data['f43'] - data['f60']) / data['f60'] * 100, 2),
            "最高": data['f44'] / 100,
            "最低": data['f45'] / 100
        }
    return results

print(get_index_data())