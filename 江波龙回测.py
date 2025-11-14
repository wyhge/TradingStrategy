import tushare as ts
import pandas as pd

# 初始化 tushare（替换成你的 token）
ts.set_token('6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9')
pro = ts.pro_api()

# 参数
# stock = "301308.SZ"  # 江波龙
stock = "300650.SZ"  # 德明利                                    

start_date = "20250911"
end_date = "20251114"
initial_capital = 10000

# 输入买入日期
buy_date_input = "2025-09-12"  # 这个日期会作为开盘买入的日子

# 获取历史数据
df = pro.daily(ts_code=stock, start_date=start_date, end_date=end_date)
df['trade_date'] = pd.to_datetime(df['trade_date'])
df = df.sort_values('trade_date').reset_index(drop=True)

# 初始化交易变量
capital = initial_capital
position = 0
trades = []
observing = False
first_high = None
buy_price = None
buy_date = None

for i in range(len(df) - 2):
    row = df.iloc[i]

    # 调试输出：每天的日期和最高价
    print(f"调试: {row['trade_date'].date()} 最高价: {row['high']}")

    # 买入逻辑
    if position == 0:
        if row['trade_date'].strftime("%Y-%m-%d") == buy_date_input:
            buy_price = row['open']  # 开盘价买
            buy_date = row['trade_date']
            position = capital / buy_price
            first_high = row['high']  # 买入当天最高价
            print(f"买入信号 -> 日期: {buy_date.date()} 开盘价: {buy_price} 当天最高价: {first_high}")
            observing = False
            continue

    # 持仓逻辑
    if position > 0:
        next_row = df.iloc[i + 1]     # 买入后的第二天
        next2_row = df.iloc[i + 2]    # 买入后的第三天

        # 第二天是阴线 -> 进入观察模式，并记录前高
        if not observing and next_row['close'] < next_row['open']:
            observing = True
            prev_high = row['high']  # 买入当天的前高
            print(f"进入观察模式 -> 记录前高: {prev_high} (买入日: {row['trade_date'].date()})")

        # 观察模式&第三天未突破前高 -> 卖出
        if observing:
            if next2_row['close'] < prev_high:
                sell_price = next2_row['close']
                sell_date = next2_row['trade_date']
                capital = position * sell_price
                print(f"卖出信号 -> 日期: {sell_date.date()} 收盘价: {sell_price} 前高: {prev_high}")
                trades.append({
                    'buy_date': buy_date,
                    'buy_price': buy_price,
                    'sell_date': sell_date,
                    'sell_price': sell_price,
                    'profit': capital - initial_capital
                })
                position = 0
                observing = False
                buy_price = None
                first_high = None
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

# 输出交易记录
if trades:
    print("\n===== 详细交易记录 =====")
    for idx, t in enumerate(trades, start=1):
        print(f"{idx}. 买入日期: {t['buy_date'].date()}  "
              f"买入价: {t['buy_price']:.2f}  "
              f"卖出日期: {t['sell_date'].date()}  "
              f"卖出价: {t['sell_price']:.2f}  "
              f"单笔盈亏: {t['profit']:.2f}")
else:
    print("\n策略期间无交易发生")