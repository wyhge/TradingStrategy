import akshare as ak
import pandas as pd
import numpy as np
import datetime

# ========== 1. 获取数据 ==========
today = datetime.date.today()

# 沪深300近60日数据（收盘价+成交量）
index_df = ak.stock_zh_index_daily(symbol="sh000300")
index_df['date'] = pd.to_datetime(index_df['date'])
index_df.sort_values("date", inplace=True)

# 近两个月数据
df = index_df.tail(60).copy()
df['MA5'] = df['close'].rolling(5).mean()
df['MA20'] = df['close'].rolling(20).mean()
df['MA60'] = df['close'].rolling(60).mean()
df['MA5_slope'] = df['MA5'].diff()
df['MA20_slope'] = df['MA20'].diff()

# 成交量均值
df['VOL_MA5'] = df['volume'].rolling(5).mean()
df['VOL_MA20'] = df['volume'].rolling(20).mean()
df['量比'] = df['volume'] / df['VOL_MA20']

# 波动率
df['Volatility'] = df['close'].rolling(20).std()

# 涨跌幅
df['涨跌幅'] = df['close'].pct_change()

# ========== 2. 北向资金 ==========
print("=== 北向资金数据获取 ===")
try:
    hsgt_df = ak.stock_hsgt_hist_em(symbol="北向资金")
    # 按日期排序，获取最近5日
    hsgt_df = hsgt_df.sort_values("日期", ascending=False).head(5)
    
    # 优先使用"当日成交净买额"，如果不可用则尝试"当日资金流入"
    if "当日成交净买额" in hsgt_df.columns:
        # 使用"当日成交净买额"（单位：万元），转换为亿元
        hsgt_df["当日资金流入"] = pd.to_numeric(hsgt_df["当日成交净买额"], errors="coerce") / 10000
    elif "当日资金流入" in hsgt_df.columns:
        # 如果"当日资金流入"存在，直接使用
        hsgt_df["当日资金流入"] = pd.to_numeric(hsgt_df["当日资金流入"], errors="coerce")
    else:
        # 如果都不存在，尝试用买入和卖出计算
        if "买入成交额" in hsgt_df.columns and "卖出成交额" in hsgt_df.columns:
            buy = pd.to_numeric(hsgt_df["买入成交额"], errors="coerce")
            sell = pd.to_numeric(hsgt_df["卖出成交额"], errors="coerce")
            hsgt_df["当日资金流入"] = (buy - sell) / 10000  # 转换为亿元
        else:
            hsgt_df["当日资金流入"] = 0
    
    north_inflow_5d = hsgt_df["当日资金流入"].sum()  # 亿元
    print(f"最近5日北向资金净流入总和: {north_inflow_5d:.2f} 亿元")
except Exception as e:
    print(f"北向资金数据获取失败: {e}")
    north_inflow_5d = 0

# ========== 3. 涨停/跌停家数 ==========
print("\n=== 涨停跌停数据获取 ===")
try:
    # 优先使用东方财富接口
    spot_df = ak.stock_zh_a_spot_em()
    print(f"使用东方财富接口获取实时股票数据成功，共 {len(spot_df)} 只股票")
    
    if '涨跌幅' in spot_df.columns:
        limit_up_df = spot_df[spot_df['涨跌幅'] >= 9.9]
        limit_down_df = spot_df[spot_df['涨跌幅'] <= -9.9]
        
        涨停数 = len(limit_up_df)
        跌停数 = len(limit_down_df)
        炸板率 = 0  # 实时数据无法获取炸板率，设置为0
        
        print(f"涨停股票数量: {涨停数}")
        print(f"跌停股票数量: {跌停数}")
    else:
        print("数据中缺少'涨跌幅'列，使用默认值")
        涨停数 = 0
        跌停数 = 0
        炸板率 = 0
except Exception as e1:
    print(f"东方财富接口获取失败: {e1}")
    try:
        # 备用方案：使用新浪接口
        spot_df = ak.stock_zh_a_spot()
        print(f"使用新浪接口获取实时股票数据成功，共 {len(spot_df)} 只股票")
        
        if '涨跌幅' in spot_df.columns:
            limit_up_df = spot_df[spot_df['涨跌幅'] >= 9.9]
            limit_down_df = spot_df[spot_df['涨跌幅'] <= -9.9]
            涨停数 = len(limit_up_df)
            跌停数 = len(limit_down_df)
            炸板率 = 0
        else:
            涨停数 = 0
            跌停数 = 0
            炸板率 = 0
    except Exception as e2:
        print(f"所有实时数据接口都失败: {e2}")
        # 如果都失败，使用默认值
        涨停数 = 0
        跌停数 = 0
        炸板率 = 0
        print("使用默认值: 涨停数=0, 跌停数=0, 炸板率=0")

# ========== 4. 因子打分函数 ==========
def score_funding(north_inflow, vol_ratio):
    score = 0
    if north_inflow > 50: score += 5
    elif north_inflow > 0: score += 3
    else: score += 1
    if vol_ratio > 1.2: score += 5
    elif vol_ratio > 0.8: score += 3
    else: score += 1
    return score / 2  # 归一化到0~5

def score_sentiment(up, down, bomb):
    score = 5
    score += (up - down) / 50
    score -= bomb * 5
    return max(0, min(score, 5))

def score_technical(ma5, ma20, ma60, slope5, slope20):
    if ma5 > ma20 > ma60 and slope5 > 0 and slope20 > 0:
        return 5
    elif ma20 > ma60 and slope20 > 0:
        return 4
    elif abs(ma20 - ma60) / ma60 < 0.02:
        return 3
    elif ma20 < ma60 and slope20 < 0:
        return 2
    else:
        return 1

def score_volatility(vol):
    if vol < df['Volatility'].mean():
        return 5
    elif vol < df['Volatility'].mean() * 1.2:
        return 4
    else:
        return 2

# ========== 5. 计算最新因子得分 ==========
latest = df.iloc[-1]
funding_score = score_funding(north_inflow_5d, latest["量比"])
sentiment_score = score_sentiment(涨停数, 跌停数, 炸板率)
technical_score = score_technical(latest["MA5"], latest["MA20"], latest["MA60"], latest["MA5_slope"], latest["MA20_slope"])
volatility_score = score_volatility(latest["Volatility"])

# 简单总分计算（权重可调）
total_score = funding_score * 0.2 + sentiment_score * 0.15 + technical_score * 0.25 + volatility_score * 0.1

# ========== 6. 环境分类 ==========
def classify_env(score):
    if score >= 4.5:
        return "主升浪"
    elif score >= 4.0:
        return "震荡向上"
    elif score >= 3.0:
        return "震荡"
    elif score >= 2.5:
        return "弱势震荡"
    elif score >= 2.0:
        return "震荡向下"
    else:
        return "单边下跌"

env_status = classify_env(total_score)

# ========== 7. 输出结果 ==========
print(f"{today} 指数环境监测结果：")
print(f"资金面得分: {funding_score:.2f}")
print(f"情绪面得分: {sentiment_score:.2f}")
print(f"技术面得分: {technical_score:.2f}")
print(f"波动率得分: {volatility_score:.2f}")
print(f"总分: {total_score:.2f} → 环境判断：{env_status}")

# 保存
result_df = pd.DataFrame([{
    "日期": today,
    "资金面得分": funding_score,
    "情绪面得分": sentiment_score,
    "技术面得分": technical_score,
    "波动率得分": volatility_score,
    "总分": total_score,
    "市场环境": env_status
}])
result_df.to_csv("A股指数环境每日监测.csv", index=False, mode="a", encoding="utf-8-sig")