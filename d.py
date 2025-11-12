import akshare as ak
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False

def get_index_data(symbol="sh000300", start_date="20240101", end_date=None):
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    df = ak.stock_zh_index_daily(symbol=symbol)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    return df[(df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))].reset_index()

def get_market_breadth():
    try:
        spot_df = ak.stock_zh_a_spot_em()
        up_count = (spot_df["涨跌幅"] > 0).sum()
        total_stocks = len(spot_df)
        up_ratio = up_count / total_stocks
        limit_up_count = (spot_df["涨跌幅"] >= 9.9).sum()
        avg_gain = spot_df["涨跌幅"].mean()
        return {
            "上涨家数占比": f"{up_ratio:.2%}",
            "涨停股数量": limit_up_count,
            "连板股数量": "需接入历史涨停接口计算",
            "市场平均涨幅": f"{avg_gain:.2f}%"
        }
    except Exception as e:
        return {"错误": f"赚钱效应获取失败：{str(e)}"}

def get_style_performance(start_date="20240101", end_date=None):
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    style_indexes = {
        "大盘价值": "sh000015", "大盘成长": "sh000016",
        "中盘价值": "sh000017", "中盘成长": "sh000018",
        "小盘价值": "sh000019", "小盘成长": "sh000020",
        "沪深300（大盘）": "sh000300", "中证500（中盘）": "sh000905",
        "中证1000（小盘）": "sh000852", "创业板指（成长）": "sz399006"
    }
    out_list = []
    for name, symbol in style_indexes.items():
        df = get_index_data(symbol=symbol, start_date=start_date, end_date=end_date)
        if len(df) < 2:
            continue
        gain = (df["close"].iloc[-1] - df["close"].iloc[0]) / df["close"].iloc[0]
        out_list.append({"风格": name, "区间涨跌幅": f"{gain:.2%}"})
    return pd.DataFrame(out_list).sort_values("区间涨跌幅", ascending=False)

def get_fund_concentration():
    try:
        industry_df = ak.stock_board_industry_name_em()
        industry_top5 = industry_df.nlargest(5, "涨跌幅")[["板块名称", "涨跌幅"]].reset_index(drop=True)
        industry_top5["涨跌幅"] = industry_top5["涨跌幅"].astype(float).round(2).astype(str) + "%"
        hsgt_df = ak.stock_hsgt_hist_em(symbol="北向资金").sort_values("日期", ascending=False).head(5)
        north_5d = hsgt_df["当日资金流入"].sum()
        return {
            "资金聚焦行业（当日涨幅前5）": industry_top5,
            "北向资金近5日净流入（亿元）": round(north_5d / 10000, 2)
        }
    except Exception as e:
        return {"错误": f"资金聚焦获取失败：{str(e)}"}

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
        df = get_index_data(self.index_symbol, self.start_date, self.end_date)
        if len(df) < self.long_period:
            return "数据不足", "请扩大时间范围", df
        df["pct_chg"] = df["close"].pct_change() * 100
        df[f"ma{self.short_period}"] = df["close"].rolling(self.short_period).mean()
        df[f"ma{self.long_period}"] = df["close"].rolling(self.long_period).mean()
        df = df.dropna()
        latest = df.iloc[-1]
        recent = df.iloc[-self.volatility_period:]
        short_above_long = latest[f"ma{self.short_period}"] > latest[f"ma{self.long_period}"]
        trend_strength = recent["pct_chg"].sum() / 100
        volatility = recent["pct_chg"].std() / 100

        if short_above_long:
            if trend_strength > self.trend_threshold and volatility < self.volatility_threshold:
                return "主升浪", "全仓，找主线和核心标的", df
            elif trend_strength > 0:
                return "震荡向上", "全仓轮动，聚焦主线", df
            else:
                return "震荡行情", "观察主线，半仓参与结构性机会", df
        else:
            if trend_strength < -self.trend_threshold and volatility < self.volatility_threshold:
                return "单边向下", "空仓观望", df
            elif trend_strength < 0:
                return "震荡向下", "小仓参与（≤30%仓位）", df
            else:
                return "震荡行情", "观察主线，半仓参与结构性机会", df

    def run_full_analysis(self):
        print(f"===== {datetime.now().strftime('%Y-%m-%d')} 市场全景分析 =====")

        env, strategy, index_df = self.judge_market_env()
        print(f"\n1. 市场大环境：{env}")
        print(f"   操作策略：{strategy}")

        breadth_data = get_market_breadth()
        print(f"\n2. 赚钱效应：")
        for key, value in breadth_data.items():
            print(f"   - {key}：{value}")

        style_df = get_style_performance(self.start_date, self.end_date)
        print(f"\n3. 赚钱风格（区间涨跌幅Top5）：")
        for idx, row in style_df.head(5).iterrows():
            print(f"   - {row['风格']}：{row['区间涨跌幅']}")

        fund_data = get_fund_concentration()
        print(f"\n4. 资金聚焦：")
        if "错误" in fund_data:
            print(f"   - {fund_data['错误']}")
        else:
            print(f"   - 北向资金近5日净流入：{fund_data['北向资金近5日净流入（亿元）']} 亿元")
            print(f"   - 当日涨幅前5行业：")
            for idx, row in fund_data["资金聚焦行业（当日涨幅前5）"].iterrows():
                print(f"     {idx+1}. {row['板块名称']}：{row['涨跌幅']}")

if __name__ == "__main__":
    analysis = MarketAnalysisWithStyle(index_symbol="sh000001", start_date="20240101")
    analysis.run_full_analysis()