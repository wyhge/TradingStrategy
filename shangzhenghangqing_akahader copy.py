import akshare as ak
import pandas as pd
from datetime import datetime  # 关键：补充导入datetime模块
def get_index_data1(symbol="sh000300", start_date="20240830"):
    """获取指数行情数据（修正日期处理）"""
    df = ak.stock_zh_index_daily(symbol=symbol)
    df["date"] = pd.to_datetime(df["date"])  # 转为datetime
    df = df.set_index("date")  # 设日期为索引
    df = df[df.index >= pd.to_datetime(start_date)]  # 筛选起始日期后的数据
    return df


def get_index_data(symbol="sh000300", start_date="20250403", end_date="20250430"):
    """获取指数行情数据（支持起始日期和结束日期筛选）"""
    # 若未指定结束日期，默认取当前日期
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    
    # 获取完整日线数据
    df = ak.stock_zh_index_daily(symbol=symbol)
    
    # 日期格式统一转换为datetime
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    
    # 筛选“起始日期≤数据日期≤结束日期”的区间数据
    df = df[
        (df.index >= pd.to_datetime(start_date)) & 
        (df.index <= pd.to_datetime(end_date))
    ]
    
    return df.reset_index()  # 重置索引，让日期作为普通列（可选，根据需求决定是否保留索引）
def _judge_with_trend(prev3, df):
    """基于连续3天的趋势判断市场环境"""
    # 主升浪：连续3天 MA5>MA10>MA20 且 close>MA5
    ma5_gt_10 = (prev3["MA5"] > prev3["MA10"]).all()
    ma10_gt_20 = (prev3["MA10"] > prev3["MA20"]).all()
    close_gt_ma5 = (prev3["close"] > prev3["MA5"]).all()
    if ma5_gt_10 and ma10_gt_20 and close_gt_ma5:
        return "主升浪", "全仓，找主线和核心"
    
    # 震荡向上：连续3天 close>MA20 且 MA5>MA10（未达主升浪）
    close_gt_ma20 = (prev3["close"] > prev3["MA20"]).all()
    if close_gt_ma20 and ma5_gt_10:
        return "震荡向上", "全仓轮动，找主线"
    
    # 震荡横盘：近3天偏离度均值 < 动态阈值（用20天波动率）
    vol = df["close"].pct_change().rolling(20).std().iloc[-1]
    dynamic_threshold = max(0.01, vol)  # 最低1%
    dev_ratio = (prev3["close"] - prev3["MA20"]).abs() / prev3["close"]
    if dev_ratio.mean() < dynamic_threshold:
        return "震荡横盘", "半仓参与"
    
    # 震荡向下：连续3天 close<MA20 且 MA5<MA10
    close_lt_ma20 = (prev3["close"] < prev3["MA20"]).all()
    ma5_lt_10 = (prev3["MA5"] < prev3["MA10"]).all()
    if close_lt_ma20 and ma5_lt_10:
        return "震荡向下", "小仓参与"
    
    # 单边向下：连续3天 MA5<MA10<MA20 且 close<MA20
    ma10_lt_20 = (prev3["MA10"] < prev3["MA20"]).all()
    if ma5_lt_10 and ma10_lt_20 and close_lt_ma20:
        return "单边向下", "空仓观望"
    
    return "不确定", "保持谨慎"

def judge_market_environment(df):
    """判断市场环境（加入趋势持续性和NaN处理）"""
    # 计算均线
    df["MA5"] = df["close"].rolling(5).mean()
    df["MA10"] = df["close"].rolling(10).mean()
    df["MA20"] = df["close"].rolling(20).mean()
    # 过滤均线未形成的数据（至少20天）
    df = df.dropna(subset=["MA20"])
    if len(df) < 3:  # 至少需要3天数据判断趋势
        return "数据不足", "请补充至少20个交易日数据"
    
    prev3 = df.iloc[-3:]  # 取最近3天数据
    return _judge_with_trend(prev3, df)

# 测试代码
if __name__ == "__main__":
    df = get_index_data(symbol="sh000300", start_date="20240101")
    env, advice = judge_market_environment(df)
    print(f"当前指数环境：{env}")
    print(f"操作建议：{advice}")