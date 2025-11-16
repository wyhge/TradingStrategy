import pandas as pd

# 读取 CSV
df = pd.read_csv('301308.SZ_turnover_ratio.csv')

# 确认列名
print("文件包含的列：", df.columns.tolist())

# 提取 ts_code 列
turnover_ratio = df['turnover_ratio'].tolist()
trade_date = df['trade_date'].tolist()
# 输出
print("提取的 ts_code 列：")
for turnover_ratio1 in turnover_ratio:
    print(turnover_ratio1)

# 如果需要保存到新的文件
pd.DataFrame({'trade_date':trade_date , 'turnover_ratio': turnover_ratio}).to_csv('turnover_ratio.csv', index=False, encoding='utf-8-sig')
print("已将 turnover_ratio 列保存到 301308.SZ_turnover_ratio.csv")