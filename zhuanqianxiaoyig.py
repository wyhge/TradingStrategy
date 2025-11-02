import akshare as ak
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 设置中文显示
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False

# ---------------------- 基础函数：数据获取（重点修改赚钱效应函数） ----------------------
def get_index_data(symbol="sh000300", start_date="20240101", end_date=None):
    """获取指数行情数据（支持时间范围筛选）"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    df = ak.stock_zh_index_daily(symbol=symbol)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    df = df[(df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))]
    return df.reset_index()

def get_market_breadth(date=None):
    """修复：用新版接口获取赚钱效应数据（上涨家数、涨停数等）"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")  # 新版接口日期格式为YYYY-MM-DD
    try:
        # 新版接口：获取A股市场概况（含上涨家数、下跌家数、平均涨幅）
        market_summary = ak.stock_a_market_summary(date=date)
        # 新版接口：获取涨停股列表（判断连板效应）
        limit_up_stocks = ak.stock_limit_up_em(date=date)
    except Exception as e:
        # 兼容部分日期格式差异，重试旧格式
        date_old = datetime.now().strftime("%Y%m%d")
        market_summary = ak.stock_a_market_summary(date=date_old)
        limit_up_stocks = ak.stock_limit_up_em(date=date_old)
    
    # 计算核心赚钱效应指标（适配新版接口字段）
    total_stocks = market_summary["上涨家数"].iloc[0] + market_summary["下跌家数"].iloc[0]
    up_ratio = market_summary["上涨家数"].iloc[0] / total_stocks  # 上涨家数占比
    limit_up_count = len(limit_up_stocks)  # 涨停股数量
    # 计算连板股数量（适配新版接口字段，可能为“连板”或“连板数”）
    consecutive_col = "连板" if "连板" in limit_up_stocks.columns else "连板数"
    consecutive_limit_up = limit_up_stocks[limit_up_stocks[consecutive_col] >= 2].shape[0]
    
    return {
        "上涨家数占比": f"{up_ratio:.2%}",
        "涨停股数量": limit_up_count,
        "连板股数量": consecutive_limit_up,
        "市场平均涨幅": f"{market_summary['平均涨幅'].iloc[0]:.2f}%"
    }

def get_style_performance(start_date="20240101", end_date=None):
    """分析赚钱风格：对比大盘/中盘/小盘、成长/价值指数涨跌幅"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    style_indexes = {
        "大盘价值": "sh000015",
        "大盘成长": "sh000016",
        "中盘价值": "sh000017",
        "中盘成长": "sh000018",
        "小盘价值": "sh000019",
        "小盘成长": "sh000020",
        "沪深300（大盘）": "sh000300",
        "中证500（中盘）": "sh000905",
        "中证1000（小盘）": "sh000852",
        "创业板指（成长）": "sz399006"
    }
    
    style_perf = []
    for name, symbol in style_indexes.items():
        df = get_index_data(symbol=symbol, start_date=start_date, end_date=end_date)
        if len(df) < 2:
            continue
        start_close = df["close"].iloc[0]
        end_close = df["close"].iloc[-1]
        gain = (end_close - start_close) / start_close
        style_perf.append({"风格": name, "区间涨跌幅": f"{gain:.2%}"})
    
    return pd.DataFrame(style_perf).sort_values("区间涨跌幅", ascending=False)

def get_fund_concentration(start_date="20240101", end_date=None):
    """定位资金聚焦方向：行业涨幅榜+北向资金流向"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    # 申万一级行业日涨幅
    industry_df = ak.stock_board_industry_name_em()
    industry_top5 = industry_df.nlargest(5, "涨跌幅")[["板块名称", "涨跌幅"]].reset_index(drop=True)
    industry_top5["涨跌幅"] = industry_top5["涨跌幅"].astype(float).round(2).astype(str) + "%"
    
    # 北向资金近5日净流入
    north_flow = ak.stock_hsgt_north_net_flow_em()
    north_5d = north_flow.head(5)["净流入金额"].sum()
    
    return {
        "资金聚焦行业（当日涨幅前5）": industry_top5,
        "北向资金近5日净流入（亿元）": round(north_5d / 10000, 2)
    }

# ---------------------- 主类：整合择时+风格分析 ----------------------
class MarketAnalysisWithStyle:
    def __init__(self, index_symbol="sh000001", start_date="20240101", end_date=None):
        self.index_symbol = index_symbol
        self.start_date = start_date
        self.end_date = end_date
        self.short_period = 20
        self.long_period = 60
        self.volatility_period = 20
        self.trend_threshold = 0.03
        self.volatility_threshold = 0.05

    def judge_market_env(self):
        """判断市场大环境（择时）"""
        df = get_index_data(self.index_symbol, self.start_date, self.end_date)
        if len(df) < self.long_period:
            return "数据不足", "请扩大时间范围", df
        df["pct_chg"] = df["close"].pct_change() * 100
        df[f"ma{self.short_period}"] = df["close"].rolling(window=self.short_period).mean()
        df[f"ma{self.long_period}"] = df["close"].rolling(window=self.long_period).mean()
        df = df.dropna()
        latest = df.iloc[-1]
        recent = df.iloc[-self.volatility_period:]
        short_above_long = latest[f"ma{self.short_period}"] > latest[f"ma{self.long_period}"]
        trend_strength = recent["pct_chg"].sum() / 100
        volatility = recent["pct_chg"].std() / 100

        if short_above_long:
            if trend_strength > self.trend_threshold and volatility < self.volatility_threshold:
                env, strategy = "主升浪", "全仓，找主线和核心标的"
            elif trend_strength > 0:
                env, strategy = "震荡向上", "全仓轮动，聚焦主线"
            else:
                env, strategy = "震荡行情", "观察主线，半仓参与结构性机会"
        else:
            if trend_strength < -self.trend_threshold and volatility < self.volatility_threshold:
                env, strategy = "单边向下", "空仓观望"
            elif trend_strength < 0:
                env, strategy = "震荡向下", "小仓参与（仓位建议≤30%）"
            else:
                env, strategy = "震荡行情", "观察主线，半仓参与结构性机会"
        return env, strategy, df

    def run_full_analysis(self):
        """完整分析：市场环境+赚钱效应+赚钱风格+资金聚焦"""
        print(f"===== {datetime.now().strftime('%Y-%m-%d')} 市场全景分析 =====")
        
        # 1. 市场大环境
        env, strategy, index_df = self.judge_market_env()
        print(f"\n1. 市场大环境：{env}")
        print(f"   操作策略：{strategy}")
        
        # 2. 赚钱效应（修复后接口）
        try:
            breadth_data = get_market_breadth()
            print(f"\n2. 赚钱效应：")
            for key, value in breadth_data.items():
                print(f"   - {key}：{value}")
        except Exception as e:
            print(f"\n2. 赚钱效应获取失败：{str(e)}（可尝试升级AKShare：pip install akshare --upgrade）")
        
        # 3. 赚钱风格
        try:
            style_df = get_style_performance(self.start_date, self.end_date)
            print(f"\n3. 赚钱风格（区间涨跌幅Top5）：")
            for idx, row in style_df.head(5).iterrows():
                print(f"   - {row['风格']}：{row['区间涨跌幅']}")
        except Exception as e:
            print(f"\n3. 赚钱风格获取失败：{str(e)}")
        
        # 4. 资金聚焦
        try:
            fund_data = get_fund_concentration()
            print(f"\n4. 资金聚焦：")
            print(f"   - 北向资金近5日净流入：{fund_data['北向资金近5日净流入（亿元）']} 亿元")
            print(f"   - 当日涨幅前5行业：")
            for idx, row in fund_data["资金聚焦行业（当日涨幅前5）"].iterrows():
                print(f"     {idx+1}. {row['板块名称']}：{row['涨跌幅']}")
        except Exception as e:
            print(f"\n4. 资金聚焦获取失败：{str(e)}")
        
        # 5. 可视化
        # self.plot_trend(index_df)

    def plot_trend(self, df):
        """可视化指数+均线趋势"""
        df[f"ma{self.short_period}"] = df["close"].rolling(window=self.short_period).mean()
        df[f"ma{self.long_period}"] = df["close"].rolling(window=self.long_period).mean()
        plt.figure(figsize=(12, 6))
        plt.plot(df["date"], df["close"], label="指数收盘价", color="blue", linewidth=2)
        plt.plot(df["date"], df[f"ma{self.short_period}"], label=f"{self.short_period}日均线", color="orange", linestyle="--")
        plt.plot(df["date"], df[f"ma{self.long_period}"], label=f"{self.long_period}日均线", color="green", linestyle="-.")
        plt.title(f"{self.index_symbol}趋势图（含均线）", fontsize=14)
        plt.xlabel("日期"), plt.ylabel("点位")
        plt.legend(), plt.grid(alpha=0.3), plt.xticks(rotation=45)
        plt.tight_layout(), plt.show()

# ---------------------- 运行分析 ----------------------
if __name__ == "__main__":
    analysis = MarketAnalysisWithStyle(
        index_symbol="sh000001",  # 上证指数
        start_date="20240101",    # 起始日期
        end_date=None             # 结束日期（默认当前）
    )
    analysis.run_full_analysis()