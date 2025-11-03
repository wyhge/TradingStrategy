import tushare as ts
import pandas as pd
from datetime import datetime

TOKEN = '6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9'
pro = ts.pro_api(TOKEN)



def get_history_data(ts_code, start_date, end_date):
    """获取合并后的历史行情、量比和资金流向数据"""
    daily = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    basic = pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date,
                            fields='ts_code,trade_date,volume_ratio')
    money = pro.moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date,
                          fields='ts_code,trade_date,buy_lg_amount,buy_elg_amount')
    # 合并
    df = daily.merge(basic, on=['ts_code','trade_date'], how='left')
    df = df.merge(money, on=['ts_code','trade_date'], how='left')
    df.sort_values('trade_date', inplace=True)
    df['ma5'] = df['close'].rolling(5).mean()
    return df

def backtest_strategy(df, initial_cash=100000):
    cash = initial_cash
    position = 0
    trade_log = []
    equity_curve = []

    for i in range(len(df)-1):
        today = df.iloc[i]
        tomorrow = df.iloc[i+1]

        # 简化强弱条件
        is_strong = (today['close'] > today['ma5']) and (today['pct_chg'] > 2)
        is_weak = (today['close'] < today['ma5'])

        if position == 0 and is_strong:
            buy_price = tomorrow['open']
            position = cash / buy_price
            cash = 0
            trade_log.append(('BUY', tomorrow['trade_date'], buy_price))
        elif position > 0 and is_weak:
            sell_price = tomorrow['open']
            cash = position * sell_price
            position = 0
            trade_log.append(('SELL', tomorrow['trade_date'], sell_price))

        if position > 0:
            net_value = cash + position * today['close']
        else:
            net_value = cash
        equity_curve.append(net_value)

    # 最后一笔平仓记录
    if position > 0:
        sell_price = df.iloc[-1]['close']
        cash = position * sell_price
        position = 0
        trade_log.append(('SELL', df.iloc[-1]['trade_date'], sell_price))
    
    final_value = cash

    # 统计胜率
    pnl_list = []
    for i in range(0, len(trade_log)-1, 2):
        if trade_log[i][0] == 'BUY' and trade_log[i+1][0] == 'SELL':
            pnl = trade_log[i+1][2] - trade_log[i][2]
            pnl_list.append(pnl)

    win_trades = sum(1 for p in pnl_list if p > 0)
    lose_trades = sum(1 for p in pnl_list if p <= 0)
    win_rate = win_trades / max(1, win_trades + lose_trades)

    return {
        "final_value": final_value,
        "win_rate": win_rate,
        "equity_curve": equity_curve,
        "trades": trade_log
    }
if __name__ == "__main__":
    # 获取所有A股基本信息
    stock_info = pro.stock_basic(exchange='', list_status='L', fields='ts_code,name')

    # 测试前10只股票（可以改成更多）
    stock_list = stock_info.head(10)['ts_code'].tolist()

    results = []
    for code in stock_list:
        print(f"\n[信息] 回测 {code} ...")
        df = get_history_data(code, start_date='20240101', end_date=datetime.now().strftime('%Y%m%d'))

        if df.empty:
            print("[警告] 无数据，跳过")
            continue

        res = backtest_strategy(df)
        results.append({
            "股票代码": code,
            "最终资金": res["final_value"],
            "胜率": res["win_rate"]
        })

    # 输出统计结果
    df_results = pd.DataFrame(results)
    print("\n批量回测结果：")
    print(df_results)
    df_results.to_excel("批量回测结果.xlsx", index=False)