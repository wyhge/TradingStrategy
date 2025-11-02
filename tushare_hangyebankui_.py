import tushare as ts
import pandas as pd
from datetime import datetime
import time

# ====== 配置你的 TuShare Token ======
TOKEN = '6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9'  # 替换成你的TuShare Token
pro = ts.pro_api(TOKEN)

def get_latest_trade_date():
    """获取最近交易日（如果今天不是交易日则取上一个交易日）"""
    today = datetime.now().strftime('%Y%m%d')
    df_trade = pro.trade_cal(exchange='', start_date='20251031', end_date=today)
    df_trade = df_trade[df_trade['is_open'] == 1]
    return df_trade.iloc[-1]['cal_date']  # 最近一个交易日

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

if __name__ == "__main__":
    # 获取最近交易日
    trade_date = get_latest_trade_date()
    print(f"[信息] 最新交易日: {trade_date}")

    # 获取所有申万行业板块
    industry_df = get_boards_chg('SW', trade_date)
    # 按涨跌幅降序排序
    industry_df.sort_values(by='涨跌幅%', ascending=False, inplace=True)

    # 取涨幅前5的行业板块
    top5_boards = industry_df.head(5)

    # 保存到 Excel
    output_file = f"前5行业板块_{trade_date}.xlsx"
    with pd.ExcelWriter(output_file) as writer:
        industry_df.to_excel(writer, sheet_name="所有行业板块", index=False)
        top5_boards.to_excel(writer, sheet_name="涨幅前5行业板块", index=False)

    print(f"[完成] 数据已保存到 {output_file}")