import tushare as ts
import pandas as pd

# 设置 token
ts.set_token('6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9')
pro = ts.pro_api()

# 参数设置
stock = "301308.SZ"  # 太龙股份
start_date = "20250912"
end_date = "20251114"
initial_capital = 10000

# 获取历史数据
df = pro.daily(ts_code=stock, start_date=start_date, end_date=end_date)
df['trade_date'] = pd.to_datetime(df['trade_date'])
df = df.sort_values('trade_date').reset_index(drop=True)

# 计算5日均线
df['ma5'] = df['close'].rolling(window=5).mean()

capital = initial_capital
position = 0
buy_price = None
buy_date = None
trades = []

# 遍历数据
for i in range(len(df) - 1):  # 至少有第二天数据
    row = df.iloc[i]
    next_row = df.iloc[i + 1]

    # 买入条件：前一天收盘价 < MA5，且第二天开盘价 > 前一天最高价
    if position == 0:
        if row['close'] < row['ma5'] and next_row['open'] > row['high']:
            buy_price = next_row['open']
            buy_date = next_row['trade_date']
            position = capital / buy_price
            print(f"买入信号 -> 日期: {buy_date.date()}, 买入价: {buy_price:.2f}")
            continue

    # 卖出条件：收盘价 < MA5（当持仓时）
    if position > 0:
        if row['close'] < row['ma5']:
            sell_price = row['close']
            sell_date = row['trade_date']
            capital = position * sell_price
            trades.append({
                'buy_date': buy_date,
                'buy_price': buy_price,
                'sell_date': sell_date,
                'sell_price': sell_price,
                'profit': capital - initial_capital
            })
            print(f"卖出信号 -> 日期: {sell_date.date()}, 卖出价: {sell_price:.2f}")
            position = 0
            buy_price = None

# 结果统计
profits = [t['profit'] for t in trades]
win_trades = [p for p in profits if p > 0]
lose_trades = [p for p in profits if p <= 0]
win_rate = len(win_trades) / len(trades) if trades else 0
avg_win = sum(win_trades) / len(win_trades) if win_trades else 0
avg_loss = abs(sum(lose_trades) / len(lose_trades)) if lose_trades else 0
odds = avg_win / avg_loss if avg_loss != 0 else None

print("\n===== 回测结果 =====")
print(f"最终资金: {capital:.2f}")
print(f"交易次数: {len(trades)}")
print(f"胜率: {win_rate:.2%}")
print(f"盈亏比: {odds if odds else '无亏损交易'}")
print(f"平均盈利: {avg_win:.2f}, 平均亏损: {avg_loss:.2f}")

if trades:
    print("\n===== 详细交易记录 =====")
    for idx, t in enumerate(trades, start=1):
        print(f"{idx}. 买入日期: {t['buy_date'].date()}  买入价: {t['buy_price']:.2f}  "
              f"卖出日期: {t['sell_date'].date()}  卖出价: {t['sell_price']:.2f}  盈亏: {t['profit']:.2f}")
else:
    print("\n策略期间无交易发生")