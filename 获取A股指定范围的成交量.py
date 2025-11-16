import tushare as ts
import pandas as pd
import time

# 初始化 tushare
ts.set_token('6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9')  # 替换成你的 Tushare token
pro = ts.pro_api()

# ===== 设置参数 =====
start_date = "20251114"  # 时间范围起始
end_date = "20251114"    # 时间范围结束
save_file = "stock_volume_stats.csv"

# ===== 获取全A股代码（排除科创板 & 北交所） =====
df_all = pro.stock_basic(exchange='', list_status='L', fields='ts_code,name')
df_all = df_all[~df_all['ts_code'].str.startswith('688')]  # 排除科创板
df_all = df_all[~df_all['ts_code'].str.endswith('.BJ')]    # 排除北交所
stock_codes = df_all['ts_code'].tolist()

print(f"A股股票数量（不含科创板、北交所）: {len(stock_codes)}")

# ===== 计算每只股票的成交量总和 & 平均 =====
results = []

for ts_code in stock_codes:
    try:
        # 获取指定时间范围的日行情
        df_daily = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if not df_daily.empty:
            total_vol = df_daily['vol'].sum()   # 成交量总和（单位：手）
            avg_vol = df_daily['vol'].mean()    # 平均成交量（单位：手）
            
            results.append({
                'ts_code': ts_code,
                'name': df_all[df_all['ts_code'] == ts_code]['name'].values[0],
                'total_vol_hand': total_vol,
                'avg_vol_hand': avg_vol
            })
    except Exception as e:
        print(f"{ts_code} 查询失败: {e}")
    time.sleep(0.05)  # 防止调用过快

# ===== 保存到 CSV =====
df_results = pd.DataFrame(results)
df_results.to_csv(save_file, index=False, encoding='utf-8-sig')

print(f"已保存成交量统计到 {save_file}")
print(df_results.head())