# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import talib
import akshare as ak
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

# 策略参数配置
class StrategyConfig:
    BREAKOUT_LOOKBACK = 20       # 突破前高观察周期
    PULLBACK_THRESHOLD = 0.03    # 回撤幅度阈值(3%)
    VOLUME_RATIO = 1.5           # 成交量放大倍数
    UPPER_SHADOW_RATIO = 2.0     # 上影线/实体比例阈值
    STOP_LOSS = 0.05             # 止损比例(5%)
    POSITION_SIZE = 0.2          # 单次建仓比例

def get_stock_data(ticker, start_date, end_date):
    """获取股票历史数据（后复权）"""
    try:
        df = ak.stock_zh_a_hist(
            symbol=ticker, period="daily", 
            start_date=start_date, end_date=end_date, adjust="hfq"
        )
        # 列名转换
        df = df.rename(columns={
            "日期": "Date", "开盘": "Open", "收盘": "Close", 
            "最高": "High", "最低": "Low", "成交量": "Volume"
        })
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.set_index('Date').sort_index()
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception as e:
        raise ValueError(f"数据获取失败: {str(e)}")

def calculate_technical_indicators(df):
    """计算技术指标"""
    # 移动均线
    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA20'] = df['Close'].rolling(20).mean()
    
    # 量能指标
    df['VOL_MA5'] = df['Volume'].rolling(5).mean()
    
    # 计算上影线和实体
    df['UpperShadow'] = df['High'] - np.maximum(df['Open'], df['Close'])
    df['Body'] = np.abs(df['Close'] - df['Open'])
    
    # 突破高点
    df['PrevHigh'] = df['High'].shift(1).rolling(StrategyConfig.BREAKOUT_LOOKBACK).max()
    
    return df.dropna()

def detect_breakout_pullback(df):
    """识别突破回抽买入信号"""
    df['BreakoutSignal'] = False
    for i in range(StrategyConfig.BREAKOUT_LOOKBACK + 5, len(df)):
        # 条件1：突破前期高点
        breakout_cond = df['Close'].iloc[i] > df['PrevHigh'].iloc[i]
        
        # 条件2：回踩确认（回撤3%-5%）
        pullback_cond = any(
            (df['Low'].iloc[j] <= df['PrevHigh'].iloc[i] * (1 - StrategyConfig.PULLBACK_THRESHOLD)) 
            for j in range(i-3, i)
        )
        
        # 条件3：放量上涨确认
        volume_cond = df['Volume'].iloc[i] > df['VOL_MA5'].iloc[i] * StrategyConfig.VOLUME_RATIO
        
        if breakout_cond and pullback_cond and volume_cond:
            df.loc[df.index[i], 'BreakoutSignal'] = True
    
    return df

def detect_long_upper_shadow(df):
    """识别长上影线卖出信号"""
    df['LongUpperShadow'] = False
    for i in range(1, len(df)):
        # 上影线长度 > 实体长度的2倍
        if df['Body'].iloc[i] > 0:  # 避免除零错误
            shadow_ratio = df['UpperShadow'].iloc[i] / df['Body'].iloc[i]
            if shadow_ratio > StrategyConfig.UPPER_SHADOW_RATIO:
                df.loc[df.index[i], 'LongUpperShadow'] = True
    
    return df

def backtest_strategy(ticker, start_date, end_date):
    """执行策略回测"""
    # 获取并处理数据
    data = get_stock_data(ticker, start_date, end_date)
    data = calculate_technical_indicators(data)
    data = detect_breakout_pullback(data)
    data = detect_long_upper_shadow(data)
    
    # 初始化交易记录
    trades = []
    position = 0
    entry_price = 0
    stop_loss = 0
    
    # 模拟交易
    for i in range(len(data)):
        # 突破回抽买入信号
        if data['BreakoutSignal'].iloc[i] and position == 0:
            position = StrategyConfig.POSITION_SIZE
            entry_price = data['Close'].iloc[i]
            stop_loss = entry_price * (1 - StrategyConfig.STOP_LOSS)
            trades.append({
                'Date': data.index[i],
                'Action': 'BUY',
                'Price': entry_price,
                'StopLoss': stop_loss
            })
        
        # 长上影线卖出信号
        elif data['LongUpperShadow'].iloc[i] and position > 0:
            sell_price = data['Close'].iloc[i]
            profit = (sell_price - entry_price) / entry_price
            trades.append({
                'Date': data.index[i],
                'Action': 'SELL',
                'Price': sell_price,
                'Profit': profit
            })
            position = 0
        
        # 止损检查
        elif position > 0 and data['Low'].iloc[i] < stop_loss:
            trades.append({
                'Date': data.index[i],
                'Action': 'STOP',
                'Price': stop_loss,
                'Profit': (stop_loss - entry_price) / entry_price
            })
            position = 0
    
    return data, trades

def visualize_results(data, trades, ticker):
    """可视化结果"""
    plt.figure(figsize=(16, 12))
    
    # 价格走势
    ax1 = plt.subplot(211)
    plt.plot(data['Close'], label='Price', color='black')
    plt.plot(data['MA10'], label='MA10', linestyle='--', alpha=0.7)
    plt.plot(data['MA20'], label='MA20', linestyle='--', alpha=0.7)
    
    # 标记买卖信号
    buy_dates = [trade['Date'] for trade in trades if trade['Action'] == 'BUY']
    buy_prices = [trade['Price'] for trade in trades if trade['Action'] == 'BUY']
    plt.scatter(buy_dates, buy_prices, marker='^', color='g', s=100, label='Buy')
    
    sell_dates = [trade['Date'] for trade in trades if trade['Action'] in ['SELL', 'STOP']]
    sell_prices = [trade['Price'] for trade in trades if trade['Action'] in ['SELL', 'STOP']]
    plt.scatter(sell_dates, sell_prices, marker='v', color='r', s=100, label='Sell')
    
    # 标记长上影线
    shadow_dates = data[data['LongUpperShadow']].index
    plt.scatter(shadow_dates, data.loc[shadow_dates, 'High'], 
                marker='x', color='purple', s=80, label='Long Upper Shadow')
    
    plt.title(f'{ticker} - Breakout Pullback & Long Upper Shadow Strategy')
    plt.legend()
    
    # 成交量
    ax2 = plt.subplot(212, sharex=ax1)
    plt.bar(data.index, data['Volume'], color='gray', alpha=0.7)
    plt.plot(data['VOL_MA5'], label='Volume MA5', color='blue')
    
    # 标记放量点
    breakout_dates = data[data['BreakoutSignal']].index
    plt.scatter(breakout_dates, data.loc[breakout_dates, 'Volume'], 
                color='red', s=50, label='Breakout Volume')
    
    plt.legend()
    plt.tight_layout()
    plt.savefig(f'{ticker}_strategy.png', dpi=300)
    plt.show()

# 主函数
if __name__ == "__main__":
    # 参数设置
    ticker = '000010'  # 隆扬电子
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
    
    try:
        print(f"▶ 开始执行策略 {ticker} [{start_date}至{end_date}]")
        data, trades = backtest_strategy(ticker, start_date, end_date)
        trades_df = pd.DataFrame(trades)
        
        if not trades_df.empty:
            # 计算累计收益
            trades_df['Cumulative_Return'] = (1 + trades_df['Profit'].fillna(0)).cumprod() - 1
            
            # 打印交易记录
            print("\n交易记录:")
            print(trades_df[['Date', 'Action', 'Price', 'Profit']])
            
            # 绩效统计
            total_trades = len(trades_df)
            winning_trades = trades_df[trades_df['Profit'] > 0].shape[0]
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            total_return = trades_df['Cumulative_Return'].iloc[-1]
            
            print("\n⭐ 策略绩效报告")
            print(f"总交易次数: {total_trades}")
            print(f"胜率: {win_rate:.2%}")
            print(f"总收益率: {total_return:.2%}")
        else:
            print("⚠️ 未产生交易信号")
        
        # 可视化结果
        visualize_results(data, trades, ticker)
        print(f"✅ 策略图已保存: {ticker}_strategy.png")
        
    except Exception as e:
        print(f"❌ 策略执行失败: {str(e)}")
        print("💡 解决方案:")
        print("1. 检查AKShare版本: pip install akshare --upgrade")
        print("2. 安装TA-Lib: https://ta-lib.org/")
        print("3. 尝试更换股票代码 (如: 600036 招商银行)")
        print("4. 缩短日期范围 (start_date='20240101', end_date='20240331')")