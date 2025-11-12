import pandas as pd
import tushare as ts

# ========== 参数配置 ==========
TUSHARE_TOKEN = "6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9"   # <<< 填入你的Tushare Token
symbol = "600519.SH"          # 股票代码（A股格式使用.SH 或 .SZ）
start_date = "20200101"       # 格式：YYYYMMDD
end_date = "20231231"
ma_period = 20                 # 均线周期
export_excel = True            # 是否导出交易记录到Excel
# ==============================

# 初始化tushare
ts.set_token(TUSHARE_TOKEN)
pro = ts.pro_api()

# 1. 获取历史数据（日K）
print(f"正在从 Tushare 获取 {symbol} 历史数据...")
df = pro.daily(ts_code=symbol, start_date=start_date, end_date=end_date)
if df.empty:
    print("⚠ 没有下载到数据，请检查代码或日期范围")
    exit()
    
# tushare数据是按日期降序，需要升序
df = df.sort_values(by="trade_date").reset_index(drop=True)

# 2. 计算策略信号
df['MA'] = df['close'].rolling(ma_period).mean()
df['Signal'] = 0
df.loc[df['close'] > df['MA'], 'Signal'] = 1
df.loc[df['close'] < df['MA'], 'Signal'] = -1

# 3. 模拟交易（按收盘价计算）
trades = []
position = 0
buy_price = 0
buy_date = None

for i, row in df.iterrows():
    if position == 0 and row['Signal'] == 1:
        position = 1
        buy_price = row['close']
        buy_date = row['trade_date']
    
    elif position == 1 and row['Signal'] == -1:
        sell_price = row['close']
        sell_date = row['trade_date']
        pct_change = (sell_price - buy_price) / buy_price
        trades.append({
            'Buy_Date': buy_date,
            'Buy_Price': buy_price,
            'Sell_Date': sell_date,
            'Sell_Price': sell_price,
            'Change_Pct': pct_change
        })
        position = 0

trade_df = pd.DataFrame(trades)

if trade_df.empty:
    print("⚠ 没有产生交易，请调整策略参数")
    exit()

# 4. 计算胜率、盈亏比、赔率、期望值
win_trades = trade_df[trade_df['Change_Pct'] > 0]
lose_trades = trade_df[trade_df['Change_Pct'] <= 0]

win_rate = len(win_trades) / len(trade_df)
avg_win = win_trades['Change_Pct'].mean() if len(win_trades) > 0 else 0
avg_loss = lose_trades['Change_Pct'].mean() if len(lose_trades) > 0 else 0
payoff_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else None
expected_value = win_rate * avg_win + (1 - win_rate) * avg_loss

# 5. 输出结果
print("\n===== 回测结果 =====")
print(f"总交易次数:       {len(trade_df)}")
print(f"胜率:             {win_rate*100:.2f}%")
print(f"平均盈利:         {avg_win*100:.2f}%")
print(f"平均亏损:         {avg_loss*100:.2f}%")
print(f"盈亏比(Payoff):   {payoff_ratio:.2f}")
print(f"期望值:           {expected_value*100:.2f}%")

# 6. 导出结果
if export_excel:
    filename = f"{symbol}_backtest_tushare.xlsx"
    trade_df.to_excel(filename, index=False)
    print(f"\n✅ 交易明细已导出到 {filename}")