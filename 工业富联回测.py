import tushare as ts
import pandas as pd

# 初始化 tushare
ts.set_token('6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9')

pro = ts.pro_api()

# 股票参数
stock = "002759.SZ"  
start_date = "20250615"
end_date = "20251115"
buy_date_input = "2025-09-26"
initial_capital = 10000

# 判断是否为创业板
is_chuangyeban = stock.startswith("3") and stock.endswith(".SZ")

# 获取数据
df = pro.daily(ts_code=stock, start_date=start_date, end_date=end_date)
df['trade_date'] = pd.to_datetime(df['trade_date'])
df = df.sort_values('trade_date').reset_index(drop=True)

# 涨跌幅 & 阴线
df['pct_chg'] = df['close'].pct_change() * 100
df['is_yin'] = df['close'] < df['open']

# 历史天量
max_vol = df['vol'].max()
max_vol_date = df.loc[df['vol'].idxmax(), 'trade_date']

capital = initial_capital
position = 0
buy_price = None
buy_date = None
trades = []

for i in range(len(df)):
    row = df.iloc[i]

    # 买入逻辑
    if position == 0:
        if row['trade_date'].strftime('%Y-%m-%d') == buy_date_input:
            buy_price = row['open']
            buy_date = row['trade_date']
            position = capital / buy_price
            print(f"买入 -> 日期: {buy_date.date()}, 买入价: {buy_price:.2f}")
            continue

    # 卖出逻辑
    if position > 0 and i > 2:
        sell_flag = False
        reason = ""

        # 1. 历史天量收阴线
        if row['trade_date'] == max_vol_date and row['is_yin']:
            sell_flag = True
            reason = "历史天量收阴线"

        # 2. 连续两天收大阴（动态阈值）
        big_drop_limit = -15 if is_chuangyeban else -8
        if df.iloc[i-1]['pct_chg'] <= big_drop_limit and row['pct_chg'] <= big_drop_limit:
            sell_flag = True
            reason = f"连续两天收大阴({big_drop_limit}%)"

        # 3. 跳空低开（动态阈值）
        drop_limit = -6 if is_chuangyeban else -3
        if row['open'] < df.iloc[i-1]['low'] and row['pct_chg'] <= drop_limit:
            sell_flag = True
            reason = f"跳空低开({drop_limit}%)"

        if sell_flag:
            sell_price = row['close']
            sell_date = row['trade_date']
            capital = position * sell_price

            pct_today = row['pct_chg']
            pct_day1 = df.iloc[i-1]['pct_chg']
            pct_day2 = df.iloc[i-2]['pct_chg']

            trades.append({
                'buy_date': buy_date,
                'buy_price': buy_price,
                'sell_date': sell_date,
                'sell_price': sell_price,
                'profit': capital - initial_capital,
                'reason': reason,
                'holding_days': (sell_date - buy_date).days,
                'pct_today': pct_today,
                'pct_day1': pct_day1,
                'pct_day2': pct_day2
            })

            print(f"卖出 -> 日期: {sell_date.date()}, 原因: {reason}, 卖出价: {sell_price:.2f}")
            print(f"  涨跌幅(卖出日): {pct_today:.2f}%")
            print(f"  涨跌幅(前1日): {pct_day1:.2f}%")
            print(f"  涨跌幅(前2日): {pct_day2:.2f}%")

            position = 0
            buy_price = None

# 输出结果
if trades:
    trade = trades[0]
    print("\n===== 回测结果 =====")
    print(f"股票代码: {stock}")
    print(f"买入日期: {trade['buy_date'].date()}")
    print(f"卖出日期: {trade['sell_date'].date()}")
    print(f"持仓天数: {trade['holding_days']} 天")
    print(f"买入价: {trade['buy_price']:.2f} | 卖出价: {trade['sell_price']:.2f}")
    print(f"盈亏: {trade['profit']:.2f}")
    print(f"卖出原因: {trade['reason']}")
    print(f"卖出日涨跌幅: {trade['pct_today']:.2f}%")
    print(f"前1日涨跌幅: {trade['pct_day1']:.2f}%")
    print(f"前2日涨跌幅: {trade['pct_day2']:.2f}%")

    # 最大回撤
    period_data = df[(df['trade_date'] >= trade['buy_date']) & (df['trade_date'] <= trade['sell_date'])]
    max_price = period_data['close'].max()
    min_price = period_data['close'].min()
    max_drawdown = (min_price - max_price) / max_price * 100
    print(f"最大回撤: {max_drawdown:.2f}%")
else:
    print("\n在设定条件下，该买入日期未产生交易。")