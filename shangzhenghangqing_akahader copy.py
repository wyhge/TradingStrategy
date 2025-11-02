import akshare as ak
import pandas as pd
import os

def get_index_data(symbol="sh000300", period="daily", start_date="20240101"):
    """
    获取指数行情数据
    symbol: 指数代码（例：sh000300是沪深300）
    period: daily, weekly, monthly
    start_date: 数据起始日期
    """
    df = ak.stock_zh_index_daily(symbol=symbol)
    df = df[df.index >= pd.to_datetime(start_date)]
    return df

def judge_market_environment(df):
    """
    根据均线与价位关系判断市场状态
    环境分类：
    - 主升浪（上涨趋势）
    - 震荡向上
    - 震荡横盘
    - 震荡向下
    - 单边向下
    """
    df["MA5"] = df["close"].rolling(5).mean()
    df["MA10"] = df["close"].rolling(10).mean()
    df["MA20"] = df["close"].rolling(20).mean()

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # 简化判断逻辑，可自行优化
    if latest["MA5"] > latest["MA10"] > latest["MA20"] and latest["close"] > latest["MA5"]:
        return "主升浪", "全仓，找主线和核心"
    elif latest["close"] > latest["MA20"] and latest["MA5"] > latest["MA10"]:
        return "震荡向上", "全仓轮动，找主线"
    elif abs(latest["close"] - latest["MA20"]) / latest["close"] < 0.01:
        return "震荡横盘", "半仓参与"
    elif latest["close"] < latest["MA20"] and latest["MA5"] < latest["MA10"]:
        return "震荡向下", "小仓参与"
    elif latest["MA5"] < latest["MA10"] < latest["MA20"] and latest["close"] < latest["MA20"]:
        return "单边向下", "空仓观望"
    else:
        return "不确定", "保持谨慎"

# def main():
df = get_index_data(symbol="sh000300", start_date="20240101")
env, advice = judge_market_environment(df)
print(f"当前指数环境：{env}")
print(f"操作建议：{advice}")

# if __name__ == "__main__":
#     main()