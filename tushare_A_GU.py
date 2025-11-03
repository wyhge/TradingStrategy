import tushare as ts
import pandas as pd
from datetime import datetime

TOKEN = '6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9'
pro = ts.pro_api(TOKEN)

def get_latest_trade_date(date=None):
    """获取最近一个交易日，如果不是交易日则回退"""
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    df_trade = pro.trade_cal(exchange='', start_date='20100101', end_date=date)
    df_open = df_trade[df_trade['is_open'] == 1]
    if date in df_open['cal_date'].values:
        return date
    else:
        latest_date = df_open.iloc[-1]['cal_date']
        print(f"[信息] {date} 非交易日，使用最近一个交易日：{latest_date}")
        return latest_date

def get_daily_data(ts_codes, trade_date):
    """获取指定股票代码列表的当日完整日线行情"""
    all_data = []
    for code in ts_codes:
        try:
            daily_df = pro.daily(ts_code=code, trade_date=trade_date)
            if not daily_df.empty:
                row = daily_df.iloc[0]
                all_data.append({
                    '股票代码': row['ts_code'],
                    '交易日期': row['trade_date'],
                    '开盘价': row['open'],
                    '最高价': row['high'],
                    '最低价': row['low'],
                    '收盘价': row['close'],
                    '昨收价': row['pre_close'],
                    '涨跌额': row['change'],
                    '涨跌幅': row['pct_chg'],
                    '成交量(手)': row['vol'],
                    '成交额(千元)': row['amount']
                })
            else:
                print(f"[警告] {code} {trade_date} 无行情数据")
        except Exception as e:
            print(f"[警告] 获取 {code} 数据失败: {e}")
    # 即使数据为空，也生成带固定列结构的 DataFrame
    return pd.DataFrame(all_data, columns=[
        '股票代码','交易日期','开盘价','最高价','最低价','收盘价','昨收价',
        '涨跌额','涨跌幅','成交量(手)','成交额(千元)'
    ])

if __name__ == "__main__":
    # 获取所有A股基本信息
    df_all_basic = pro.stock_basic(exchange='', list_status='L', fields='ts_code,name')
    print(f"[完成] 共获取 {len(df_all_basic)} 只A股基本信息")

    stock_list = df_all_basic.head(100)['ts_code'].tolist()

    # 确定交易日
    # trade_date = get_latest_trade_date(datetime.now().strftime('%Y%m%d'))
    trade_date = '20251103'  # 指定日期测试
    print(f"[信息] 获取交易日: {trade_date}")

    # 获取数据
    df_daily = get_daily_data(stock_list, trade_date)

    if '涨跌幅' in df_daily.columns:
        # 筛选条件：涨幅 > 5%
        filtered_df = df_daily[df_daily['涨跌幅'] > 5]
        print(f"[信息] 符合条件的股票数量: {len(filtered_df)}")

        txt_file = f"涨幅大于5的股票_{trade_date}.txt"
        filtered_df.to_csv(txt_file, sep='\t', index=False, encoding='utf-8')
        print(f"[完成] 已保存到 {txt_file}")
    else:
        print("[错误] 没有涨跌幅列，可能是当天无行情数据或全部股票数据空")