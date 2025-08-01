# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import talib
import akshare as ak
import matplotlib.pyplot as plt
import os
import warnings
from backtesting import Backtest, Strategy
from datetime import datetime

# 忽略警告
warnings.filterwarnings("ignore")

# 策略参数配置（修复类名大小写）
class AShareStrategyConfig:  
    SECONDARY_TEST_VOL_RATIO = 1.8   
    JUMP_CREEK_VOL_RATIO = 2.0
    BREAKOUT_VOL_RATIO = 1.5
    VOLUME_MA_WINDOW = 5
    HEAD_SHOULDER_MIN_PERCENT = 0.15
    STOP_LOSS_PERCENT = 0.03
    POSITION_SIZE = 0.2

# 数据获取函数（支持缓存）
def get_ashare_data(ticker, start_date, end_date):
    cache_file = f"{ticker}_{start_date}_{end_date}.pkl"
     
     #缓存机制减少 API调用
    if os.path.exists(cache_file):
        return pd.read_pickle(cache_file)
    
    try:
        # AKShare数据获取 [6,8](@ref)
        df = ak.stock_zh_a_hist(
            symbol=ticker,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="hfq"
        )
        
        # 列名转换（关键修复）
        df = df.rename(columns={
            "日期": "Date",
            "开盘": "Open",
            "收盘": "Close",
            "最高": "High",
            "最低": "Low",
            "成交量": "Volume"
        })
        
        # 日期处理
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.set_index('Date').sort_index()
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df = df.dropna()
        df.to_pickle(cache_file)
        return df
        
    except Exception as e:
        raise ValueError(f"数据获取失败: {str(e)}")

# 技术指标计算（解决长度不一致问题）
def calculate_technical_indicators(df):
    # 基础指标 移动均线
    df['MA5'] = df['Close'].rolling(5, min_periods=1).mean()
    df['MA10'] = df['Close'].rolling(10, min_periods=1).mean()
    df['MA20'] = df['Close'].rolling(20, min_periods=1).mean()
    df['VOL_MA5'] = df['Volume'].rolling(5, min_periods=1).mean()
    
    # MACD（处理NaN值）
    macd, macd_signal, _ = talib.MACD(df['Close'], 12, 26, 9)
    df['MACD'] = macd
    df['MACD_Signal'] = macd_signal
    
    # RSI
    df['RSI'] = talib.RSI(df['Close'], 14)
    
    # 布林带
    upper, middle, lower = talib.BBANDS(df['Close'], 20)
    df['UpperBB'] = upper
    df['MiddleBB'] = middle
    df['LowerBB'] = lower
    
    # 量价指标
    df['Volume_Ratio'] = df['Volume'] / df['VOL_MA5'].replace(0, 1e-5)
    
    # 缺口检测（1% 阈值）
    df['Gap_Up'] = df['Low'] > df['High'].shift(1) * 1.01
    df['Gap_Down'] = df['High'] < df['Low'].shift(1) * 0.99
    
    return df.fillna(0)

# 形态识别（修复SettingWithCopyWarning）
def detect_patterns(df):
    df = df.copy()  # 显式创建副本
    df['Secondary_Test'] = False
    df['Jump_Creek'] = False
    df['Head_Shoulder_Bottom'] = False
    
    # 二次测试（威科夫）
    for i in range(2, len(df)):  
        if (df['Volume_Ratio'].iloc[i-2] > AShareStrategyConfig.SECONDARY_TEST_VOL_RATIO and  #放量上涨
            df['Close'].iloc[i-2] > df['Open'].iloc[i-2] and
            df['Volume_Ratio'].iloc[i-1] < 0.8 and   #缩量回调
            df['Close'].iloc[i-1] < df['Open'].iloc[i-1] and
            df['Low'].iloc[i] > df['Low'].iloc[i-1]):  # 低点抬高
            df.loc[df.index[i], 'Secondary_Test'] = True
    
    # 跳跃小溪（威科夫）
    for i in range(1, len(df)):
        if (df['Volume_Ratio'].iloc[i] > AShareStrategyConfig.JUMP_CREEK_VOL_RATIO and   # 突破放量
            df['Close'].iloc[i] > df['UpperBB'].iloc[i] and  # 突破 布林上轨
            df['Close'].iloc[i] > df['High'].rolling(window=20).max().iloc[i-1]):  # 突破20日高点
            df.loc[df.index[i], 'Jump_Creek'] = True
    
    # 头肩底形态
    for i in range(4, len(df)):
        left_shoulder = df['Low'].iloc[i-4]
        head = df['Low'].iloc[i-2]
        right_shoulder = df['Low'].iloc[i]
        neckline = min(df['High'].iloc[i-3], df['High'].iloc[i-1])
        
        if (head < left_shoulder and head < right_shoulder and   # 头部低于双肩
            abs(left_shoulder - right_shoulder) < 0.02 * left_shoulder and  # 双肩对称
            (head - min(left_shoulder, right_shoulder)) > AShareStrategyConfig.HEAD_SHOULDER_MIN_PERCENT * head and # 最小波动15%
            df['Close'].iloc[i] > neckline and  # 收盘突破颈线
            df['Volume'].iloc[i] > df['Volume'].iloc[i-2]):
            df.loc[df.index[i], 'Head_Shoulder_Bottom'] = True
    
    return df

# 交易策略类（修复指标引用）
class AShareStrategy(Strategy):
    def init(self):
        self.df = calculate_technical_indicators(self.data.df)
        self.df = detect_patterns(self.df)
        
        # 确保指标长度匹配 [6](@ref)
        self.secondary_test = self.I(lambda: np.array(self.df['Secondary_Test']), name='Secondary_Test')
        self.jump_creek = self.I(lambda: np.array(self.df['Jump_Creek']), name='Jump_Creek')
        self.head_shoulder = self.I(lambda: np.array(self.df['Head_Shoulder_Bottom']), name='Head_Shoulder')
        self.volume_ratio = self.I(lambda: np.array(self.df['Volume_Ratio']), name='Volume_Ratio')
        self.rsi = self.I(lambda: np.array(self.df['RSI']), name='RSI')
        self.ma10 = self.I(lambda: np.array(self.df['MA10']), name='MA10')
    
    def next(self):
        if len(self.data) < 30: return
            
        # 买入信号逻辑
        if not self.position:
            if self.secondary_test[-1]:
                stop_loss = self.data.Low[-1] * (1 - AShareStrategyConfig.STOP_LOSS_PERCENT)
                self.buy(size=AShareStrategyConfig.POSITION_SIZE, sl=stop_loss)  # 3% 止损
            
            elif self.jump_creek[-1]:
                stop_loss = self.data.Low[-1] * (1 - AShareStrategyConfig.STOP_LOSS_PERCENT)
                self.buy(size=AShareStrategyConfig.POSITION_SIZE, sl=stop_loss)
            
            elif self.head_shoulder[-1]:
                stop_loss = min(self.data.Low[-3], self.data.Low[-1]) * 0.98
                self.buy(size=AShareStrategyConfig.POSITION_SIZE, sl=stop_loss)
            
            elif (self.data.Close[-1] > self.data.High[-20:].max() and 
                  self.data.Close[-1] > self.ma10[-1] and
                  self.volume_ratio[-1] > AShareStrategyConfig.BREAKOUT_VOL_RATIO):
                stop_loss = self.ma10[-1] * 0.98
                self.buy(size=AShareStrategyConfig.POSITION_SIZE, sl=stop_loss)
        
        # 卖出逻辑
        else:
             # 上影线止损（影线>2倍实体）
            upper_shadow = self.data.High[-1] - max(self.data.Open[-1], self.data.Close[-1])
            body = abs(self.data.Close[-1] - self.data.Open[-1])
            if body > 0 and upper_shadow > 2 * body:
                self.position.close()
                return
               # 趋势线止损（跌破MA10）
            if self.data.Close[-1] < self.ma10[-1]:
                self.position.close()
                return
            if hasattr(self.data, 'Gap_Down') and self.data.Gap_Down[-1] and self.position.pl_pct < 0:
                self.position.close()
                return
            if self.rsi[-1] > 70:
                self.position.close()
                return

# 回测执行函数
def backtest_strategy(ticker, start_date, end_date):
    data = get_ashare_data(ticker, start_date, end_date)
    
    # 数据校验
    required_cols = {'Open', 'High', 'Low', 'Close', 'Volume'}
    if not required_cols.issubset(data.columns):
        missing = required_cols - set(data.columns)
        raise ValueError(f"缺失关键列: {missing}")
    if data.empty:
        raise ValueError("获取到空数据，请检查参数")
    
    # 执行回测 [8](@ref)
     # 10万初始资金
      # 0.2%手续费
    bt = Backtest(data, AShareStrategy, cash=100000, commission=.002)
    stats = bt.run()
    
    # 输出结果
    print(stats)
    bt.plot(filename=f"{ticker}_backtest.html")
    stats['_trades'].to_csv(f"{ticker}_trades.csv")
    return stats

# 主函数（含异常处理）
if __name__ == "__main__":
    ticker = '600519'       # 贵州茅台
    start_date = '20250728'
    end_date = '20250801'
    
    try:
        print(f"▶ 开始回测 {ticker} [{start_date}至{end_date}]")
        results = backtest_strategy(ticker, start_date, end_date)
        
        # 性能报告 [7](@ref)
        print("\n⭐ 策略绩效报告")
        print(f"夏普比率: {results['Sharpe Ratio']:.2f}")
        print(f"最大回撤: {results['Max. Drawdown [%]']:.2f}%")
        print(f"总收益率: {results['Return [%]']:.2f}%")
        print(f"年化收益: {results['Return (Ann.) [%]']:.2f}%")
        print(f"交易次数: {results['# Trades']}")
        print(f"胜率: {results['Win Rate [%]']:.2f}%")
        
        # 可视化信号
        data = get_ashare_data(ticker, start_date, end_date)
        data = calculate_technical_indicators(data)
        data = detect_patterns(data)
        
        plt.figure(figsize=(14, 8))
        plt.plot(data['Close'], label='价格')
        plt.plot(data['MA10'], label='MA10', alpha=0.7)
        plt.plot(data['UpperBB'], label='布林上轨', linestyle='--', alpha=0.5)
        plt.plot(data['LowerBB'], label='布林下轨', linestyle='--', alpha=0.5)
        
        # 标记信号
        signals = data[data['Secondary_Test'] | data['Jump_Creek'] | data['Head_Shoulder_Bottom']]
        plt.scatter(signals.index, signals['Close'], 
                    marker='^', color='green', s=100, label='买入信号')
        
        plt.title(f"{ticker} 交易信号")
        plt.legend()
        plt.grid(alpha=0.3)
        plt.savefig(f"{ticker}_signals.png", dpi=300)
        print(f"✅ 信号图已保存: {ticker}_signals.png")
        plt.show()
        
    except Exception as e:
        print(f"❌ 回测失败: {str(e)}")
        print("💡 解决方案:")
        print("1. 检查AKShare版本: pip install akshare --upgrade")
        print("2. 安装TA-Lib依赖: https://ta-lib.org/")
        print("3. 尝试更换股票代码 (如: 600036 招商银行)")
        print("4. 缩短日期范围 (start_date='20240101', end_date='20240331')")