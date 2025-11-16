import tushare as ts
import pandas as pd

# 初始化 tushare
ts.set_token('6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9')
pro = ts.pro_api()

# ===== 设置参数 =====
ts_code = "301308.SZ"  # 股票代码
start_date = "20250313"
end_date = "20251114"
save_file = f"{ts_code}_turnover_ratio.csv"  # 保存文件名

# ===== 获取日线数据 =====
df_price = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

# 获取 daily_basic 的流通市值 circ_mv（单位：万元）
df_basic = pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date,
                           fields="ts_code,trade_date,circ_mv")

if df_price.empty or df_basic.empty:
    print(f"{ts_code} 在 {start_date} ~ {end_date} 没有交易数据")
else:
    # 合并价格和流通市值
    df = pd.merge(df_price, df_basic, on=["ts_code", "trade_date"], how="left")
    df = df.sort_values('trade_date', ascending=True).reset_index(drop=True)

    # 计算流通股本（股）
    df['circ_shares'] = (df['circ_mv'] * 1e4) / df['close']  # 流通市值转成元再除以收盘价

    # 成交量单位是手，需要转成股
    df['vol_shares'] = df['vol'] * 100

    # 换手率 = 成交股数 / 流通股本 × 100%
    df['turnover_ratio'] = df['vol_shares'] / df['circ_shares'] * 100

    # 输出结果
    print(f"{ts_code} 在 {start_date} ~ {end_date} 的换手率：\n")
    print(df[['trade_date', 'turnover_ratio']])

    # 平均换手率
    avg_turnover = df['turnover_ratio'].mean()
    print(f"\n平均换手率: {avg_turnover:.2f}%")

    # ===== 保存到 CSV =====
    df.to_csv(save_file, index=False, encoding="utf-8-sig")
    print(f"\n已将结果保存到 {save_file}")