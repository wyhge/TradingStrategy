import tushare as ts
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 设置中文显示
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题

class MarketTiming:
    def __init__(self, token):
        """初始化Tushare接口和参数"""
        ts.set_token(token)
        self.pro = ts.pro_api()
        # 指数代码（上证指数）
        self.index_code = "000001.SH"
        # 趋势判断参数（可根据需要调整）
        self.short_period = 20  # 短期均线周期（20日线）
        self.long_period = 60   # 长期均线周期（60日线）
        self.volatility_period = 20  # 波动率计算周期
        self.trend_threshold = 0.03  # 趋势强度阈值（3%）
        self.volatility_threshold = 0.05  # 波动率阈值（5%）

    def get_index_data(self, days=120):
        """获取指数历史数据（默认120天，足够计算均线和趋势）"""
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        
        # 调用Tushare Pro接口获取指数日线数据
        df = self.pro.index_daily(
            ts_code=self.index_code,
            start_date=start_date,
            end_date=end_date
        )
        
        # 数据处理：转换日期格式，按日期升序排列
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.sort_values("trade_date").reset_index(drop=True)
        
        # 计算均线和涨跌幅
        df["close"] = df["close"].astype(float)  # 指数收盘价
        df["pct_chg"] = df["pct_chg"].astype(float)  # 涨跌幅（%）
        df[f"ma{self.short_period}"] = df["close"].rolling(window=self.short_period).mean()  # 短期均线
        df[f"ma{self.long_period}"] = df["close"].rolling(window=self.long_period).mean()   # 长期均线
        
        return df.dropna()  # 去除均线计算的NaN值

    def judge_trend(self, df):
        """根据指数数据判断当前市场环境"""
        # 取最新数据
        latest = df.iloc[-1]
        # 取近期数据（用于计算趋势强度和波动率）
        recent = df.iloc[-self.volatility_period:]
        
        # 1. 计算趋势方向：短期均线是否在长期均线上方
        short_above_long = latest[f"ma{self.short_period}"] > latest[f"ma{self.long_period}"]
        
        # 2. 计算趋势强度：近期累计涨幅（判断是否主升/单边下跌）
        trend_strength = recent["pct_chg"].sum() / 100  # 累计涨跌幅（转为小数）
        
        # 3. 计算波动率：近期涨跌幅的标准差（判断是否震荡）
        volatility = recent["pct_chg"].std() / 100  # 波动率（转为小数）
        
        # 4. 判断市场环境
        if short_above_long:
            # 短期均线在长期均线上方（偏多）
            if trend_strength > self.trend_threshold and volatility < self.volatility_threshold:
                # 累计涨幅大且波动率低 → 主升浪
                return "主升浪", "全仓，找主线和核心标的"
            elif trend_strength > 0:
                # 累计上涨但未达主升浪 → 震荡向上
                return "震荡向上", "全仓轮动，聚焦主线"
            else:
                # 短期均线在上方但累计下跌 → 震荡行情
                return "震荡行情", "观察主线，半仓参与结构性机会"
        else:
            # 短期均线在长期均线下方（偏空）
            if trend_strength < -self.trend_threshold and volatility < self.volatility_threshold:
                # 累计跌幅大且波动率低 → 单边向下
                return "单边向下", "空仓观望"
            elif trend_strength < 0:
                # 累计下跌但未达单边 → 震荡向下
                return "震荡向下", "小仓参与（仓位建议≤30%）"
            else:
                # 短期均线在下方但累计上涨 → 震荡行情
                return "震荡行情", "观察主线，半仓参与结构性机会"

    def plot_index(self, df):
        """可视化指数和均线"""
        plt.figure(figsize=(12, 6))
        plt.plot(df["trade_date"], df["close"], label="上证指数收盘价", color="blue")
        plt.plot(df["trade_date"], df[f"ma{self.short_period}"], label=f"{self.short_period}日均线", color="orange")
        plt.plot(df["trade_date"], df[f"ma{self.long_period}"], label=f"{self.long_period}日均线", color="green")
        plt.title("上证指数趋势图（含均线）")
        plt.xlabel("日期")
        plt.ylabel("指数点位")
        plt.grid(alpha=0.3)
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    def run(self):
        """执行主流程：获取数据→判断趋势→输出结果"""
        print("正在获取指数数据...")
        df = self.get_index_data()
        if df.empty:
            print("获取数据失败，请检查网络或Token")
            return
        
        trend, strategy = self.judge_trend(df)
        print(f"\n当前市场环境判断：{trend}")
        print(f"对应操作策略：{strategy}")
        
        # 可视化指数趋势
        self.plot_index(df)


if __name__ == "__main__":
    # 替换为你的Tushare Pro Token（从https://tushare.pro/user/token获取）
    TUSHARE_TOKEN = "6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9"  # 例如："6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9"
    # ts.set_token('6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9')
    # if TUSHARE_TOKEN == "6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9":
    #     print("请先替换TUSHARE_TOKEN为你的实际Token")
    # else:
    timing = MarketTiming(TUSHARE_TOKEN)
    timing.run()