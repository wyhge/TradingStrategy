import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime

def get_stock_data(stock_code, start_date='20200101', end_date='20231231'):
    """
    获取股票历史数据并格式化为backtrader需要的格式
    """
    try:
        # 获取后复权数据
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                               start_date=start_date, end_date=end_date, 
                               adjust="hfq")
        
        # 重命名列以符合backtrader要求
        df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '最高': 'high', 
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume'
        }, inplace=True)
        
        # 转换日期格式
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        return df
    except Exception as e:
        print(f"获取{stock_code}数据失败: {e}")
        return None

# 获取沪深300成分股作为股票池（简化版）
def get_stock_pool():
    """获取沪深300成分股"""
    stock_info = ak.stock_info_a_code_name()
    # 这里简化处理，实际应该获取准确的沪深300成分股
    return stock_info['code'].head(100).tolist()  # 取前100只作为示例

a = get_stock_pool()
print(a)