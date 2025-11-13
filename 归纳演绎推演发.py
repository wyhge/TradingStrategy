import pandas as pd
import numpy as np
import tushare as ts
import ta  # 技术指标库

# ===== 参数配置 =====
TUSHARE_TOKEN = "6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9"   # 在 Tushare 官网申请
symbol = "000001.SZ"
start_date = "20200101"
end_date = "20241231"
initial_capital = 10000
export_excel = True
# =====================

ts.set_token(TUSHARE_TOKEN)
pro = ts.pro_api()

print(f"下载 {symbol} 历史日K数据...")
df = pro.daily(ts_code=symbol, start_date=start_date, end_date=end_date)
df = df.sort_values("trade_date").reset_index(drop=True)

# === 1. 计算技术指标 ===
df['MA20'] = df['close'].rolling(20).mean()
df['MA60'] = df['close'].rolling(60).mean()
df['RSI'] = ta.momentum.RSIIndicator(df['close'], 14).rsi()
df['Volume_MA5'] = df['vol'].rolling(5).mean()
df['Price_Change'] = df['close'].pct_change()
df.dropna(inplace=True)

# === 2. 归纳法：寻找买点共性 ===
# 模拟：未来N天涨幅 > 5% 记为上涨期
N = 5
threshold = 0.05
df['Future_Return'] = df['close'].shift(-N) / df['close'] - 1
df['Up_Flag'] = df['Future_Return'] > threshold  # 未来涨幅超过阈值

# 统计上涨期前的指标特征均值
buy_point_summary = df[df['Up_Flag']].describe()[['MA20', 'RSI', 'vol']]
sell_point_summary = df[~df['Up_Flag']].describe()[['MA20', 'RSI', 'vol']]

print("\n===== 归纳法：上涨前买点特征 =====")
print(buy_point_summary)
print("\n===== 归纳法：下跌前特征 =====")
print(sell_point_summary)

# === 3. 演绎法：规则（基于共性，结合理论手工设定） ===
# 假设：当RSI<30（超卖）且 MA20 > MA60 且成交量放大是买点
df['Signal'] = 0
df.loc[(df['RSI'] < 30) & (df['MA20'] > df['MA60']) & (df['vol'] > df['Volume_MA5']*1.5), 'Signal'] = 1
# 卖点：当 RSI>70（超买）或收盘价跌破 MA20
df.loc[(df['RSI'] > 70) | (df['close'] < df['MA20']), 'Signal'] = -1

# === 4. 回测 ===
trades = []
position = 0
capital = initial_capital
buy_price = None
buy_date = None

for i, row in df.iterrows():
    if position == 0 and row['Signal'] == 1:
        position = 1
        buy_price = row['close']
        buy_date = row['trade_date']
    elif position == 1 and row['Signal'] == -1:
        sell_price = row['close']
        sell_date = row['trade_date']
        pct = (sell_price - buy_price) / buy_price
        capital *= (1 + pct)
        trades.append({
            'Buy_Date': buy_date,
            'Buy_Price': buy_price,
            'Sell_Date': sell_date,
            'Sell_Price': sell_price,
            'Change_Pct': pct,
            'Capital_After_Trade': capital
        })
        position = 0

trade_df = pd.DataFrame(trades)
if trade_df.empty:
    print("⚠ 没有产生交易，请调整规则")
else:
    win_trades = trade_df[trade_df['Change_Pct'] > 0]
    lose_trades = trade_df[trade_df['Change_Pct'] <= 0]

    win_rate = len(win_trades) / len(trade_df)
    avg_win = win_trades['Change_Pct'].mean() if not win_trades.empty else 0
    avg_loss = lose_trades['Change_Pct'].mean() if not lose_trades.empty else 0
    payoff_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else None
    expected_value = win_rate * avg_win + (1 - win_rate) * avg_loss
    total_return_pct = (capital - initial_capital) / initial_capital * 100

    print("\n===== 回测结果 =====")
    print(f"总交易次数: {len(trade_df)}")
    print(f"胜率: {win_rate*100:.2f}%")
    print(f"平均盈利: {avg_win*100:.2f}%")
    print(f"平均亏损: {avg_loss*100:.2f}%")
    print(f"盈亏比: {payoff_ratio:.2f}")
    print(f"期望值: {expected_value*100:.2f}%")
    print(f"初始资金: {initial_capital:,.2f} 元")
    print(f"最终资金: {capital:,.2f} 元")
    print(f"总收益率: {total_return_pct:.2f}%")

    if export_excel:
        trade_df.to_excel(f"{symbol}_trade_records.xlsx", index=False)
        print(f"✅ 交易记录已导出到 {symbol}_trade_records.xlsx")