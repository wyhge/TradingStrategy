import tushare as ts
import pandas as pd
import time

# 初始化 tushare
ts.set_token('6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9')
pro = ts.pro_api()

# === 回测时间范围 ===
start_date = "20250101"
end_date   = "20251115"
lookback_days = 3  # 前3日检查涨停
forward_days  = 3  # 后3日计算涨幅
save_file = "main_board_limitup_forward3d.csv"

# === 从 CSV 获取股票池 ===
df_csv = pd.read_csv('Ashare_no_kcb_bj.csv')  # 确保有 ts_code 列和 name 列
print("文件包含的列：", df_csv.columns.tolist())

# 股票代码列表
main_board_codes = df_csv['ts_code'].tolist()

# 股票代码和名称映射字典
code_name_map = dict(zip(df_csv['ts_code'], df_csv.get('name', df_csv['ts_code'])))

print(f"股票池数量: {len(main_board_codes)}")

# === 获取时间范围内所有交易日 ===
trade_dates_df = pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date)
trade_dates = trade_dates_df[trade_dates_df['is_open'] == 1]['cal_date'].tolist()

results = []

# === 遍历交易日 ===
for current_date in trade_dates:
    df_today = pro.daily(trade_date=current_date)
    df_today = df_today[df_today['ts_code'].isin(main_board_codes)]
    df_positive = df_today[df_today['pct_chg'] > 0]

    if df_positive.empty:
        continue

    print(f"\n=== {current_date} 涨幅为正个股 ===")

    for _, row in df_positive.iterrows():
        ts_code = row['ts_code']
        name = code_name_map.get(ts_code, ts_code)  # 从映射字典取股票名
        # print(f"{ts_code} {name} 今日涨幅: {row['pct_chg']:.2f}%")

        # time.sleep(0.05)  # 防止API调用太快

        try:
            # 获取当前日期往前的历史数据
            his_df = pro.daily(ts_code=ts_code, end_date=current_date)
            his_df = his_df.sort_values('trade_date', ascending=False).reset_index(drop=True)

            if len(his_df) >= lookback_days + 1:
                prev3_df = his_df.iloc[1:lookback_days+1]
                has_limitup = (prev3_df['pct_chg'] >= 9.9).any()

                if has_limitup:
                    # 获取后3日数据
                    fwd_df = pro.daily(ts_code=ts_code, start_date=current_date)
                    fwd_df = fwd_df.sort_values('trade_date').reset_index(drop=True)

                    if len(fwd_df) > forward_days:
                        price_now = fwd_df.loc[0, 'close']
                        price_fwd = fwd_df.loc[forward_days, 'close']
                        fwd_pct = (price_fwd - price_now) / price_now * 100
                    else:
                        fwd_pct = None

                    results.append({
                        'date': current_date,
                        'ts_code': ts_code,
                        'name': name,
                        'today_pct': row['pct_chg'],
                        'has_limitup_prev3d': True,
                        'forward3d_pct': fwd_pct
                    })
        except Exception as e:
            print(f"{ts_code} 查询失败: {e}")

# === 保存结果 ===
df_results = pd.DataFrame(results)
df_results.to_csv(save_file, index=False, encoding="utf-8-sig")

print(f"\n回测完成，符合条件记录数: {len(df_results)}，已保存到 {save_file}")
print(df_results.head())