import pandas as pd
import yfinance as yf

def backtest(symbol, start_date, end_date, ma_period=20, export_excel=True):
    """回测策略并计算胜率、盈亏比、期望值"""
    
    # 1. 下载数据
    print(f"正在下载 {symbol} 历史数据...")
    df = yf.download(symbol, start=start_date, end=end_date)
    df.dropna(inplace=True)
    df.reset_index(inplace=True)
    
    # 2. 策略：收盘价突破均线买入，跌破均线卖出
    df['MA'] = df['Close'].rolling(ma_period).mean()
    df['Signal'] = 0
    df.loc[df['Close'] > df['MA'], 'Signal'] = 1
    df.loc[df['Close'] < df['MA'], 'Signal'] = -1

    # 3. 模拟交易
    trades = []
    position = 0
    buy_price = 0
    buy_date = None

    for i, row in df.iterrows():
        if position == 0 and row['Signal'] == 1:
            position = 1
            buy_price = row['Close']
            buy_date = row['Date']
        
        elif position == 1 and row['Signal'] == -1:
            sell_price = row['Close']
            sell_date = row['Date']
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
        return None
    
    # 4. 计算指标
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
    
    # 6. 导出 Excel
    if export_excel:
        filename = f"{symbol}_backtest.xlsx"
        trade_df.to_excel(filename, index=False)
        print(f"\n交易明细已导出到 {filename}")
    
    return trade_df


if __name__ == "__main__":
    # 示例：贵州茅台（600519.SS），2020-2023
    # A股：在Yahoo的代码一般是 “股票代码.SS” 或 “股票代码.SZ”，
    # 美股直接用代码，例如 "AAPL"
    symbol = "600519.SS"
    start_date = "2020-01-01"
    end_date = "2023-12-31"
    
    backtest(symbol, start_date, end_date, ma_period=20)