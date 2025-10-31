import requests

def get_sector_rank():
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        'pn': '1',
        'pz': '20',  # 前20个板块
        'po': '1',
        'np': '1',
        'fltt': '2',
        'invt': '2',
        'fid': 'f3',
        'fs': 'm:90 t:2 f:!50',  # 板块类别: 行业板块
        'fields': 'f12,f13,f14,f3,f62,f128,f136,f140'
    }
    resp = requests.get(url, params=params).json()
    data = resp['data']['diff']
    return [{
        "板块": d['f14'],
        "涨跌幅%": d['f3'],
        "主力净流入(万)": d['f62']
    } for d in data]

print(get_sector_rank())