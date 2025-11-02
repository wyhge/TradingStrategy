import tushare as ts
import pandas as pd
from datetime import datetime

TOKEN = '6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9'
pro = ts.pro_api(TOKEN)

# 获取最近一个交易日
def get_latest_trade_date():
    today = datetime.now().strftime('%Y%m%d')
    df_trade = pro.trade_cal(exchange='', start_date='20251031', end_date=today)
    df_trade = df_trade[df_trade['is_open'] == 1]
    latest_date = df_trade.iloc[-1]['cal_date']  # 最近一个开盘日
    return latest_date

# 获取最新A股数据
def get_latest_a_stock_data():
    trade_date = get_latest_trade_date()
    print(f"[信息] 最新交易日: {trade_date}")

    # 股票基础信息（代码+名称+行业）
    df_basic = pro.stock_basic(exchange='', list_status='L',
                               fields='ts_code,name,industry')

    # 当日行情（收盘价+涨跌幅）
    df_daily = pro.daily(trade_date=trade_date)[['ts_code', 'close', 'pct_chg']]

    # 当日资金流向（主力流入）
    df_moneyflow = pro.moneyflow(trade_date=trade_date)[
        ['ts_code', 'buy_lg_amount', 'buy_elg_amount']
    ]
    df_moneyflow['主力流入(万元)'] = df_moneyflow['buy_lg_amount'] + df_moneyflow['buy_elg_amount']

    # 合并数据
    df_merge = df_basic.merge(df_daily, on='ts_code', how='left')
    df_merge = df_merge.merge(df_moneyflow[['ts_code', '主力流入(万元)']], on='ts_code', how='left')

    # 处理空值
    df_merge['close'] = df_merge['close'].fillna(0)
    df_merge['pct_chg'] = df_merge['pct_chg'].fillna(0)
    df_merge['主力流入(万元)'] = df_merge['主力流入(万元)'].fillna(0)

    # ========= 分情况过滤 =========
    df_merge['code_prefix'] = df_merge['ts_code'].str[:3]  # 取股票代码前3位
    condition = (
        ((df_merge['code_prefix'].isin(['300', '688'])) & (df_merge['pct_chg'] >= 15)) |
        (~df_merge['code_prefix'].isin(['300', '688']) & (df_merge['pct_chg'] >= 5))
    )
    df_merge = df_merge[condition]

    # 按涨幅降序排列
    df_merge = df_merge.sort_values(by='pct_chg', ascending=False)

    return trade_date, df_merge

# 保存到 txt 文件
if __name__ == "__main__":
    trade_date, latest_df = get_latest_a_stock_data()

    # 保存到TXT
    file_name = f"A股最新数据_{trade_date}.txt"
    latest_df.to_csv(file_name, sep='\t', index=False, encoding='utf-8')

    print(f"[完成] 已保存到 {file_name}，共保存 {len(latest_df)} 条记录")
    print(latest_df.head(10))  # 显示前10行