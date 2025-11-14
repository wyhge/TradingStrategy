import tushare as ts
import pandas as pd
import matplotlib.pyplot as plt
import datetime as dt

# ===== 初始化 tushare（替换为你自己的 token）
ts.set_token('6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9')
pro = ts.pro_api()

# ===== 参数
start_date = '20230101'
end_date = '20231231'
initial_capital = 10000

# ===== 获取日行情（这里用某只股票示例）
stock = '300750.SZ'  # 宁德时代
df = pro.daily(ts_code=stock, start_date=start_date, end_date=end_date)

# 转换日期格式 & 排序
df['trade_date'] = pd.to_datetime(df['trade_date'])
df = df.sort_values('trade_date')
df.set_index('trade_date', inplace=True)

# 计算 MA5
df['ma5'] = df['close'].rolling(5).mean()

# ===== 模拟市场情绪指标：用每天涨停家数（limit_up）来判断情绪周期
# 获取全市场每日涨停家数
all_daily = pro.daily(start_date=start_date, end_date=end_date)
limit_up_count = all_daily[all_daily['pct_chg'] >= 9]['trade_date'].value_counts()
limit_up_count = limit_up_count.rename('limit_up_num').reset_index().rename(columns={'index': 'trade_date'})
limit_up_count['trade_date'] = pd.to_datetime(limit_up_count['trade_date'])

# 合并情绪数据
df = df.reset_index().merge(limit_up_count, on='trade_date', how='left').fillna(0)

# ===== 回测逻辑
capital = initial_capital
position = 0
buy_price = 0
buy_date = None
hold_days = 0
trades = []

prev_limit_up = None
for i, row in df.iterrows():
    # 情绪拐点判断：涨停家数从下降 → 上升
    if prev_limit_up is not None:
        emotion_up = (row['limit_up_num'] > prev_limit_up)  # 情绪回暖
    else:
        emotion_up = False
    prev_limit_up = row['limit_up_num']

    # === 买入逻辑 ===
    if position == 0:
        if emotion_up and row['close'] > row['ma5']:
            buy_price = row['close']
            position = capital / buy_price
            buy_date = row['trade_date']
            hold_days = 0

    # === 卖出逻辑 ===
    elif position > 0:
        hold_days += 1
        # 卖出条件：持股 3 天 或 跌破 MA5
        if hold_days >= 3 or row['close'] < row['ma5']:
            sell_price = row['close']
            capital = position * sell_price
            trades.append({
                'buy_date': buy_date,
                'buy_price': buy_price,
                'sell_date': row['trade_date'],
                'sell_price': sell_price,
                'profit': capital - initial_capital
            })
            position = 0

# ===== 结果统计
profits = [t['profit'] for t in trades]
win_trades = [p for p in profits if p > 0]
lose_trades = [p for p in profits if p <= 0]
win_rate = len(win_trades) / len(trades) if trades else 0
avg_win = sum(win_trades) / len(win_trades) if win_trades else 0
avg_loss = abs(sum(lose_trades) / len(lose_trades)) if lose_trades else 0
odds = avg_win / avg_loss if avg_loss != 0 else None

print(f"最终资金: {capital:.2f}")
print(f"交易次数: {len(trades)}")
print(f"胜率: {win_rate:.2%}")
# print(f"盈亏比: {odds:.2f}")
print(f"平均盈利: {avg_win:.2f}, 平均亏损: {avg_loss:.2f}")

# # ===== 绘制资金曲线
# capital_curve = pd.DataFrame(trades)
# capital_curve['capital'] = initial_capital + capital_curve['profit'].cumsum()
# plt.plot(capital_curve['sell_date'], capital_curve['capital'])
# plt.xticks(rotation=45)
# plt.title("情绪周期 + 龙头逻辑 回测资金曲线")
# plt.xlabel("日期")
# plt.ylabel("资金")
# plt.grid(True)
# plt.show()