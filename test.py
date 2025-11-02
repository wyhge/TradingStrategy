import tushare as ts

# df = ts.get_hist_data('000875')
# #直接保存
# df.to_csv('c:/day/000875.csv')

# #选择保存
# df.to_csv('c:/day/000875.csv',columns=['open','high','low','close'])

# pro = ts.pro_api()

# # df = pro.index_daily(ts_code='399300.SZ')

# # #或者按日期取

# # df = pro.index_daily(ts_code='399300.SZ', start_date='20180101', end_date='20181010')

# df = pro.query('daily', ts_code='000001.SZ', start_date='20180701', end_date='20180718')
# print(df)

pro = ts.pro_api()

#设置你的token
df = pro.user(token='6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9')

print(df)