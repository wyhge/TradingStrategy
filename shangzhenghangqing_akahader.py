import akshare as ak
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 设置中文显示
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题

class MarketTimingWithAK:
    def __init__(self):
        """初始化参数（AKShare无需Token）"""
        # 指数代码（AKShare中上证指数为"sh000001"）
        self.index_code = "sh000001"
        self.index_name = "上证指数"
        
        # 趋势判断参数（可根据需要调整）
        self.short_period = 20  # 短期均线周期（20日线）
        self.long_period = 60   # 长期均线周期（60日线）
        self.volatility_period = 20  # 波动率计算周期（20天）
        self.trend_threshold = 0.03  # 趋势强度阈值（3%）
        self.volatility_threshold = 0.05  # 波动率阈值（5%）

    def get_index_data(self, days=120):
        """通过AKShare获取指数历史数据（默认120天）"""
        print(f"正在获取{self.index_name}数据...")
        
        # 调用AKShare接口获取上证指数日线数据（包含开盘价、收盘价、涨跌幅等）
        # AKShare的stock_zh_index_daily接口返回数据格式：date, open, close, high, low, volume, amount
        df = ak.stock_zh_index_daily(symbol=self.index_code)
        
        # 截取最近days天的数据（若数据不足则取全部）
        df = df.tail(days).reset_index()
        
        # 数据处理：字段对齐和格式转换
        df = df.rename(columns={"date": "trade_date"})  # 日期字段重命名
        df["trade_date"] = pd.to_datetime(df["trade_date"])  # 转换为datetime格式
        
        # 计算涨跌幅（AKShare部分接口可能不含涨跌幅，手动计算：(今日收盘价-昨日收盘价)/昨日收盘价 * 100）
        if "pct_chg" not in df.columns:
            df["pct_chg"] = df["close"].pct_change() * 100  # 涨跌幅（%）
        
        # 计算均线
        df[f"ma{self.short_period}"] = df["close"].rolling(window=self.short_period).mean()  # 短期均线
        df[f"ma{self.long_period}"] = df["close"].rolling(window=self.long_period).mean()   # 长期均线
        
        return df.dropna()  # 去除均线计算的空值

    def judge_market_env(self, df):
        """根据指数数据判断当前市场环境"""
        # 取最新数据和近期数据
        latest = df.iloc[-1]  # 最新一天的数据
        recent_data = df.iloc[-self.volatility_period:]  # 最近20天的数据
        
        # 1. 趋势方向：短期均线是否在长期均线上方（偏多/偏空）
        short_above_long = latest[f"ma{self.short_period}"] > latest[f"ma{self.long_period}"]
        
        # 2. 趋势强度：近期累计涨跌幅（判断主升/单边下跌）
        trend_strength = recent_data["pct_chg"].sum() / 100  # 转为小数（如3% → 0.03）
        
        # 3. 波动率：近期涨跌幅的标准差（判断是否震荡）
        volatility = recent_data["pct_chg"].std() / 100  # 转为小数（如5% → 0.05）
        
        # 4. 市场环境判断逻辑
        if short_above_long:
            # 短期均线在长期均线上方（偏多环境）
            if trend_strength > self.trend_threshold and volatility < self.volatility_threshold:
                return "主升浪", "全仓，找主线和核心标的"
            elif trend_strength > 0:
                return "震荡向上", "全仓轮动，聚焦主线"
            else:
                return "震荡行情", "观察主线，半仓参与结构性机会"
        else:
            # 短期均线在长期均线下方（偏空环境）
            if trend_strength < -self.trend_threshold and volatility < self.volatility_threshold:
                return "单边向下", "空仓观望"
            elif trend_strength < 0:
                return "震荡向下", "小仓参与（仓位建议≤30%）"
            else:
                return "震荡行情", "观察主线，半仓参与结构性机会"

    def plot_index_trend(self, df):
        """可视化指数走势和均线"""
        plt.figure(figsize=(12, 6))
        plt.plot(df["trade_date"], df["close"], label=f"{self.index_name}收盘价", color="blue", linewidth=2)
        plt.plot(df["trade_date"], df[f"ma{self.short_period}"], label=f"{self.short_period}日均线", color="orange", linestyle="--")
        plt.plot(df["trade_date"], df[f"ma{self.long_period}"], label=f"{self.long_period}日均线", color="green", linestyle="-.")
        
        plt.title(f"{self.index_name}趋势图（含均线）", fontsize=14)
        plt.xlabel("日期", fontsize=12)
        plt.ylabel("指数点位", fontsize=12)
        plt.grid(alpha=0.3)
        plt.legend(fontsize=10)
        plt.xticks(rotation=45)
        plt.tight_layout()  # 自动调整布局，避免标签重叠
        plt.show()

    def run(self):
        """主流程：获取数据→判断环境→输出结果→可视化"""
        # 获取指数数据
        df = self.get_index_data()
        if df.empty:
            print("数据获取失败，请检查网络或指数代码")
            return
        
        # 判断市场环境
        env, strategy = self.judge_market_env(df)
        
        # 输出结果
        print(f"\n{datetime.now().strftime('%Y-%m-%d')} {self.index_name}市场环境判断：")
        print(f"当前环境：{env}")
        print(f"操作策略：{strategy}")
        
        # 可视化趋势
        # self.plot_index_trend(df)


if __name__ == "__main__":
    # 实例化并运行
    market_timing = MarketTimingWithAK()
    market_timing.run()