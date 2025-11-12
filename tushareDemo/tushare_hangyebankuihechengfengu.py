import tushare as ts
import pandas as pd
from datetime import datetime
import time

TOKEN = '6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9'
pro = ts.pro_api(TOKEN)

def get_latest_trade_date():
    """获取最近交易日"""
    today = datetime.now().strftime('%Y%m%d')
    df_trade = pro.trade_cal(exchange='', start_date='20251031', end_date=today)
    df_trade = df_trade[df_trade['is_open'] == 1]
    return df_trade.iloc[-1]['cal_date']

def get_boards_chg(market_type, trade_date):
    """获取指定市场的所有板块涨跌幅"""
    boards = pro.index_basic(market=market_type)
    data_list = []
    for _, row in boards.iterrows():
        index_code = row['ts_code']
        index_name = row['name']
        try:
            daily = pro.index_daily(ts_code=index_code, trade_date=trade_date)
            if not daily.empty:
                pct_chg = daily.iloc[0]['pct_chg']
                data_list.append({
                    '板块代码': index_code,
                    '板块名称': index_name,
                    '涨跌幅%': pct_chg
                })
        except Exception as e:
            print(f"[警告] {index_name}({index_code}) 获取失败: {e}")
        time.sleep(0.25)  # 控制调用速度
    return pd.DataFrame(data_list)

def get_board_members_with_data(index_code, trade_date):
    """获取板块成分股数据（收盘价、涨跌幅、主力流入）"""
    members_df = pro.index_member(index_code=index_code)
    stock_list = members_df['con_code'].tolist()
    result = []
    for ts_code in stock_list:
        try:
            name_df = pro.stock_basic(ts_code=ts_code)
            name = name_df.iloc[0]['name'] if not name_df.empty else ""
            daily = pro.daily(ts_code=ts_code, trade_date=trade_date)
            close_price = daily.iloc[0]['close'] if not daily.empty else None
            pct_chg = daily.iloc[0]['pct_chg'] if not daily.empty else None
            money = pro.moneyflow(ts_code=ts_code, trade_date=trade_date)
            main_inflow = None
            if not money.empty:
                main_inflow = money.iloc[0]['buy_lg_amount'] + money.iloc[0]['buy_elg_amount']
            result.append({
                '股票代码': ts_code,
                '股票名称': name,
                '收盘价': close_price,
                '涨跌幅(%)': pct_chg,
                '主力流入(万元)': main_inflow
            })
        except Exception as e:
            print(f"[警告] 获取 {ts_code} 数据失败: {e}")
        # time.sleep(0.1)
    return pd.DataFrame(result)

if __name__ == "__main__":
    trade_date = get_latest_trade_date()
    print(f"[信息] 最新交易日: {trade_date}")

    # 获取所有申万行业板块数据
    industry_df = get_boards_chg('SW', trade_date)
    industry_df.sort_values(by='涨跌幅%', ascending=False, inplace=True)

    # 取涨跌幅前10的行业板块
    top10_boards = industry_df.head(1)

    # 保存板块及成分股数据到一个 Excel
    output_file = f"前10行业板块及成分股_{trade_date}.xlsx"
    with pd.ExcelWriter(output_file) as writer:
        industry_df.to_excel(writer, sheet_name="所有行业板块", index=False)
        for _, row in top10_boards.iterrows():
            print(f"[信息] 获取板块 {row['板块名称']} 的成分股数据...")
            members_df = get_board_members_with_data(row['板块代码'], trade_date)
            members_df.to_excel(writer, sheet_name=row['板块名称'][:30], index=False)

    print(f"[完成] 数据已保存到 {output_file}")