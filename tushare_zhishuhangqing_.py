import tushare as ts
import pandas as pd
from datetime import datetime

# TuShare 配置
TOKEN = '6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9'
pro = ts.pro_api(TOKEN)

def get_latest_trade_date():
    today = datetime.now().strftime('%Y%m%d')
    df_trade = pro.trade_cal(exchange='', start_date='20251031', end_date=today)
    df_trade = df_trade[df_trade['is_open'] == 1]
    return df_trade.iloc[-1]['cal_date']

def get_main_index_data(trade_date=None):
    if trade_date is None:
        trade_date = get_latest_trade_date()
    print(f"[信息] 最新交易日: {trade_date}")

    main_indexes = [
        '000001.SH','000300.SH','399001.SZ','399006.SZ',
        '000905.SH','000852.SH'
    ]

    all_data = []
    for ts_code in main_indexes:
        try:
            df_daily = pro.index_daily(ts_code=ts_code, trade_date=trade_date)
            if not df_daily.empty:
                all_data.append(df_daily[['ts_code','pct_chg','vol','amount']])
        except Exception as e:
            print(f"[警告] {ts_code} 获取行情失败: {e}")

    df_index_daily = pd.concat(all_data, ignore_index=True)

    # 主力流入（部分指数支持）
    try:
        df_money = pro.index_money_flow(trade_date=trade_date)[
            ['ts_code','buy_lg_amount','buy_elg_amount']
        ]
        df_money['主力流入(万元)'] = df_money['buy_lg_amount'] + df_money['buy_elg_amount']
        df_index_daily = df_index_daily.merge(df_money[['ts_code','主力流入(万元)']], on='ts_code', how='left')
    except:
        df_index_daily['主力流入(万元)'] = 0

    return trade_date, df_index_daily

if __name__ == '__main__':
    trade_date, df_index = get_main_index_data()
    print(df_index)
    df_index.to_excel(f"主要指数数据_{trade_date}.xlsx", index=False)