import pandas as pd
import numpy as np
import talib
import yfinance as yf
import matplotlib.pyplot as plt
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

# 策略参数配置
class AShareStrategyConfig:
    # 威科夫策略参数
    SECONDARY_TEST_VOL_RATIO = 1.8  # 二次测试放量比例
    JUMP_CREEK_VOL_RATIO = 2.0      # 跳跃小溪放量比例
    
    # 量价策略参数
    BREAKOUT_VOL_RATIO = 1.5        # 突破放量比例
    VOLUME_MA_WINDOW = 5            # 成交量均线窗口
    
    # 形态识别参数
    HEAD_SHOULDER_MIN_PERCENT = 0.15  # 头肩形态最小波动幅度
    TRIANGLE_MIN_SWINGS = 3           # 三角形最小波动次数
    
    # 风险管理参数
    STOP_LOSS_PERCENT = 0.03         # 止损百分比
    POSITION_SIZE = 0.2              # 单笔交易仓位比例

# 技术指标计算
def calculate_technical_indicators(df):
    # 基础指标
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['VOL_MA5'] = df['Volume'].rolling(window=5).mean()
    
    # MACD指标
    df['MACD'], df['MACD_Signal'], _ = talib.MACD(df['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
    
    # RSI指标
    df['RSI'] = talib.RSI(df['Close'], timeperiod=14)
    
    # 布林带
    df['UpperBB'], df['MiddleBB'], df['LowerBB'] = talib.BBANDS(df['Close'], timeperiod=20)
    
    # 威科夫量价指标
    df['Volume_Ratio'] = df['Volume'] / df['VOL_MA5']
    
    # 缺口检测
    df['Gap_Up'] = df['Low'] > df['High'].shift(1) * 1.01  # 1%以上缺口
    df['Gap_Down'] = df['High'] < df['Low'].shift(1) * 0.99
    
    return df.dropna()

# 形态识别函数
def detect_patterns(df):
    # 二次测试 (威科夫)
    df['Secondary_Test'] = False
    for i in range(2, len(df)):
        # 放量上涨+缩量回调+低点抬高
        if (df['Volume_Ratio'].iloc[i-2] > AShareStrategyConfig.SECONDARY_TEST_VOL_RATIO and
            df['Close'].iloc[i-2] > df['Open'].iloc[i-2] and
            df['Volume_Ratio'].iloc[i-1] < 0.8 and
            df['Close'].iloc[i-1] < df['Open'].iloc[i-1] and
            df['Low'].iloc[i] > df['Low'].iloc[i-1]):
            df['Secondary_Test'].iloc[i] = True
    
    # 跳跃小溪 (威科夫)
    df['Jump_Creek'] = False
    for i in range(1, len(df)):
        # 放量突破关键阻力
        if (df['Volume_Ratio'].iloc[i] > AShareStrategyConfig.JUMP_CREEK_VOL_RATIO and
            df['Close'].iloc[i] > df['UpperBB'].iloc[i] and
            df['Close'].iloc[i] > df['High'].rolling(window=20).max().iloc[i-1]):
            df['Jump_Creek'].iloc[i] = True
    
    # 头肩底形态 (简化版)
    df['Head_Shoulder_Bottom'] = False
    for i in range(4, len(df)):
        left_shoulder = df['Low'].iloc[i-4]
        head = df['Low'].iloc[i-2]
        right_shoulder = df['Low'].iloc[i]
        neckline = min(df['High'].iloc[i-3], df['High'].iloc[i-1])
        
        if (head < left_shoulder and head < right_shoulder and
            abs(left_shoulder - right_shoulder) < 0.02 * left_shoulder and
            (head - min(left_shoulder, right_shoulder)) > AShareStrategyConfig.HEAD_SHOULDER_MIN_PERCENT * head and
            df['Close'].iloc[i] > neckline and
            df['Volume'].iloc[i] > df['Volume'].iloc[i-2]):
            df['Head_Shoulder_Bottom'].iloc[i] = True
    
    return df

# 交易策略实现
class AShareStrategy(Strategy):
    def init(self):
        super().init()
        # 预先计算所有指标
        self.df = calculate_technical_indicators(self.data.df)
        self.df = detect_patterns(self.df)
        
        # 将计算好的指标添加到策略中
        self.secondary_test = self.I(lambda: self.df['Secondary_Test'], name='Secondary_Test')
        self.jump_creek = self.I(lambda: self.df['Jump_Creek'], name='Jump_Creek')
        self.head_shoulder = self.I(lambda: self.df['Head_Shoulder_Bottom'], name='Head_Shoulder')
        self.volume_ratio = self.I(lambda: self.df['Volume_Ratio'], name='Volume_Ratio')
    
    def next(self):
        # 如果没有持仓
        if not self.position:
            # 二次测试买入信号
            if self.secondary_test[-1]:
                stop_loss = self.data.Low[-1] * (1 - AShareStrategyConfig.STOP_LOSS_PERCENT)
                self.buy(size=ASHareStrategyConfig.POSITION_SIZE, sl=stop_loss)
            
            # 跳跃小溪买入信号
            elif self.jump_creek[-1]:
                stop_loss = self.data.Low[-1] * (1 - AShareStrategyConfig.STOP_LOSS_PERCENT)
                self.buy(size=ASHareStrategyConfig.POSITION_SIZE, sl=stop_loss)
            
            # 头肩底形态买入信号
            elif self.head_shoulder[-1]:
                stop_loss = min(self.data.Low[-3], self.data.Low[-1]) * 0.98
                self.buy(size=ASHareStrategyConfig.POSITION_SIZE, sl=stop_loss)
            
            # 突破回踩买入 (MA10)
            elif (self.data.Close[-1] > self.data.High[-20:].max() and 
                  self.data.Close[-1] > self.data.MA10[-1] and
                  self.volume_ratio[-1] > AShareStrategyConfig.BREAKOUT_VOL_RATIO):
                stop_loss = self.data.MA10[-1] * 0.98
                self.buy(size=ASHareStrategyConfig.POSITION_SIZE, sl=stop_loss)
        
        # 持仓状态下的卖出逻辑
        else:
            # 上影线止损 (当日上影线超过实体2倍)
            upper_shadow = self.data.High[-1] - max(self.data.Open[-1], self.data.Close[-1])
            body = abs(self.data.Close[-1] - self.data.Open[-1])
            if upper_shadow > 2 * body and body > 0:
                self.position.close()
            
            # 趋势线跌破止损 (MA10)
            elif self.data.Close[-1] < self.data.MA10[-1]:
                self.position.close()
            
            # 缺口理论止损 (衰竭缺口)
            elif self.data.Gap_Down[-1] and self.position.pl_pct < 0:
                self.position.close()
            
            # 获利了结 (RSI超买)
            elif self.data.RSI[-1] > 70:
                self.position.close()

# 回测执行函数
def backtest_strategy(ticker, start_date, end_date):
    # 获取数据 (这里使用yfinance，实际应用中应替换为A股数据源)
    data = yf.download(ticker, start=start_date, end=end_date)
    data = data.rename(columns={'Open': 'open', 'High': 'high', 
                               'Low': 'low', 'Close': 'close', 
                               'Volume': 'volume'})
    
    # 添加日期索引
    data = data.reset_index()
    data['Date'] = pd.to_datetime(data['Date'])
    data = data.set_index('Date')
    
    # 运行回测
    bt = Backtest(data, AShareStrategy, cash=100000, commission=.002)
    stats = bt.run()
    
    # 输出结果
    print(stats)
    bt.plot()
    
    # 保存交易明细
    trades = stats['_trades']
    trades.to_csv(f'{ticker}_trades.csv')
    
    return stats

# 主执行函数
if __name__ == "__main__":
    # 回测示例股票 (实际应用中替换为A股代码)
    ticker = '600927.SS'  # 永安期货
    start_date = '2024-01-01'
    end_date = '2025-07-31'
    
    # 执行回测
    results = backtest_strategy(ticker, start_date, end_date)
    
    # 策略性能分析
    print(f"夏普比率: {results['Sharpe Ratio']:.2f}")
    print(f"最大回撤: {results['Max. Drawdown [%]']:.2f}%")
    print(f"总收益率: {results['Return [%]']:.2f}%")
    print(f"交易次数: {results['# Trades']}")
    
    # 可视化关键信号点
    data = yf.download(ticker, start=start_date, end=end_date)
    data = calculate_technical_indicators(data)
    data = detect_patterns(data)
    
    plt.figure(figsize=(14, 10))
    
    # 价格走势
    ax1 = plt.subplot(211)
    plt.plot(data['Close'], label='Price')
    plt.plot(data['MA10'], label='MA10')
    
    # 标记买入信号
    buy_signals = data[data['Secondary_Test'] | data['Jump_Creek'] | data['Head_Shoulder_Bottom']]
    plt.scatter(buy_signals.index, buy_signals['Close'], 
                marker='^', color='green', s=100, label='Buy Signal')
    
    plt.title(f'{ticker} Price Chart with Trading Signals')
    plt.legend()
    
    # 成交量
    ax2 = plt.subplot(212, sharex=ax1)
    plt.bar(data.index, data['Volume'], color='gray', alpha=0.3)
    plt.plot(data['VOL_MA5'], color='blue', label='Volume MA5')
    
    # 标记放量点
    high_vol = data[data['Volume_Ratio'] > AShareStrategyConfig.BREAKOUT_VOL_RATIO]
    plt.scatter(high_vol.index, high_vol['Volume'], 
                color='red', s=50, label='High Volume')
    
    plt.title('Volume Analysis')
    plt.legend()
    plt.tight_layout()
    plt.savefig(f'{ticker}_signals.png')
    plt.show()