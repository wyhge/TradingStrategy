import pandas as pd
import numpy as np
import tushare as ts
import ta  # 技术指标库

# ===== 参数配置 =====
TUSHARE_TOKEN = "6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9"
symbol_list = ["600519.SH", "000858.SZ"]  # 示例股票池
start_date = "20220101"
end_date = "20231231"
initial_capital = 100000
ma_short = 5  # 短均线周期
export_excel = True
# ====================

ts.set_token(TUSHARE_TOKEN)
pro = ts.pro_api()

def get_stock_data(ts_code, start_date, end_date):
    df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    df = df.sort_values("trade_date").reset_index(drop=True)
    df['MA5'] = df['close'].rolling(ma_short).mean()
    df['Volume_MA5'] = df['vol'].rolling(5).mean()
    return df.dropna()

def generate_signals(df):
    df['Signal'] = 0
    # 买点规则：沿5日线低吸 + 成交量放大
    buy_cond = (df['close'] >= df['MA5'] * 0.98) & (df['vol'] > df['Volume_MA5'] * 1.2)
    # 卖点规则：5日线跌破 + 成交量缩小
    sell_cond = (df['close'] < df['MA5']) | (df['vol'] < df['Volume_MA5'] * 0.8)
    df.loc[buy_cond, 'Signal'] = 1
    df.loc[sell_cond, 'Signal'] = -1
    return df

def backtest(df, initial_capital):
    position = 0
    capital = initial_capital
    buy_price = 0
    trades = []

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
                "Buy_Date": buy_date,
                "Buy_Price": buy_price,
                "Sell_Date": sell_date,
                "Sell_Price": sell_price,
                "Change_Pct": pct,
                "Capital_After_Trade": capital
            })
            position = 0

    trade_df = pd.DataFrame(trades)
    if trade_df.empty:
        return None

    # 计算绩效
    win_trades = trade_df[trade_df['Change_Pct'] > 0]
    lose_trades = trade_df[trade_df['Change_Pct'] <= 0]
    win_rate = len(win_trades) / len(trade_df)
    avg_win = win_trades['Change_Pct'].mean() if not win_trades.empty else 0
    avg_loss = lose_trades['Change_Pct'].mean() if not lose_trades.empty else 0
    payoff_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else None
    total_return_pct = (capital - initial_capital) / initial_capital * 100

    print(f"总交易次数: {len(trade_df)} | 胜率: {win_rate*100:.2f}% | 盈亏比: {payoff_ratio:.2f} | 总收益率: {total_return_pct:.2f}%")
    return trade_df

# ===== 主程序 =====
all_trades = []

for sym in symbol_list:
    df = get_stock_data(sym, start_date, end_date)
    df = generate_signals(df)
    trade_df = backtest(df, initial_capital)
    if trade_df is not None:
        trade_df["Symbol"] = sym
        all_trades.append(trade_df)

# 合并交易记录并输出
if all_trades:
    final_df = pd.concat(all_trades)
    if export_excel:
        final_df.to_excel("strategy_trades.xlsx", index=False)
        print("✅ 交易记录已导出 strategy_trades.xlsx")