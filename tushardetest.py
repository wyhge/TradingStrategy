import tushare as ts


# 1. 设置你的token（从https://tushare.pro/user/token获取）
# ts.set_token('你的token')  # 替换为你的实际token：6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9
ts.set_token('6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9')
# 2. 初始化Pro接口对象（必须步骤）
pro = ts.pro_api()

# 3. 调用新版接口获取历史数据（以“000001.SZ”为例，深市股票后缀.SZ，沪市后缀.SH）
df = pro.daily(
    ts_code='000001.SZ',  # 股票代码（必须带后缀）
    start_date='20230101',  # 开始日期（格式YYYYMMDD）
    end_date='20231231'   # 结束日期（格式YYYYMMDD）
)

# 4. 数据处理（新版返回数据默认按日期降序排列，可反转排序）
df = df.sort_values(by='trade_date')  # 按日期升序排列
print(df)
