import tushare as ts
import pandas as pd

# 初始化 tushare
ts.set_token('6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9')  # 请替换成你的 token
pro = ts.pro_api()

# 获取全部上市 A 股股票信息
df_stocks = pro.stock_basic(exchange='', list_status='L',
                            fields='ts_code,name,market,exchange')

# 过滤掉科创板（688开头）和北交所（.BJ）
df_filtered = df_stocks[
    ~(
        df_stocks['ts_code'].str.startswith('688') |  # 排除科创板
        df_stocks['ts_code'].str.endswith('.BJ')      # 排除北交所
    )
]

# 输出结果
print("总股票数（排除科创板/北交所）:", len(df_filtered))
print(df_filtered.head())

# 转为列表
target_stocks = df_filtered['ts_code'].tolist()
print("前20个代码:", target_stocks[:20])

# 保存到文件
df_filtered.to_csv("A股所有代码.csv", index=False, encoding="utf-8-sig")
print("已保存到 A股所有代码.csv")