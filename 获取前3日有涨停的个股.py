import tushare as ts
import pandas as pd
import time

# 初始化 tushare
ts.set_token('6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9')
pro = ts.pro_api()

# --- 配置参数 ---
today_date = "20251114"  # 当天日期
lookback_days = 3        # 检查前3日
save_file = "selected_stocks.csv"

# 获取当前所有A股代码，并排除科创板和北交所
df_all = pro.stock_basic(exchange='', list_status='L', fields='ts_code,name')
df_all = df_all[~df_all['ts_code'].str.startswith('688')]               # 排除科创板
df_all = df_all[~df_all['ts_code'].str.endswith('.BJ')]                 # 排除北交所
target_stocks = df_all['ts_code'].tolist()

print(f"总股票数（排除科创板 & 北交所）：{len(target_stocks)}")

# 获取当天行情，过滤排除后的股票池
df_today = pro.daily(trade_date=today_date)
df_today = df_today[df_today['ts_code'].isin(target_stocks)]

# 合并股票基础信息
df_today = df_today.merge(df_all, on='ts_code', how='left')

# 过滤当天涨幅为正
df_today = df_today[df_today['pct_chg'] > 0]

selected_stocks = []

for idx, row in df_today.iterrows():
    ts_code = row['ts_code']
    name = row['name']

    # 板块类型判断：创业板涨停标准 19.8%，主板涨停标准 9.9%
    if ts_code.startswith("300") and ts_code.endswith(".SZ"):
        limit_up = 19.8
    else:
        limit_up = 9.9

    # 防止调用过快
    time.sleep(0.1)

    try:
        # 获取该股票当日之前3天行情
        his_df = pro.daily(ts_code=ts_code, end_date=today_date)
        his_df = his_df.sort_values('trade_date', ascending=False).reset_index(drop=True)

        if len(his_df) >= (lookback_days + 1):
            prev_days = his_df.iloc[1:lookback_days+1]  # 前3日
            has_limitup = (prev_days['pct_chg'] >= limit_up).any()

            print(f"[{name}] {ts_code} 今日涨幅: {row['pct_chg']:.2f}% | 前3日涨停: {has_limitup}")

            if has_limitup:
                selected_stocks.append({
                    'ts_code': ts_code,
                    'name': name
                })
    except Exception as e:
        print(f"{ts_code} 查询失败: {e}")

# 保存结果
selected_df = pd.DataFrame(selected_stocks)
selected_df.to_csv(save_file, index=False, encoding="utf-8-sig")

print("\n符合条件的股票：")
print(selected_df)
print(f"\n已保存到文件：{save_file}")