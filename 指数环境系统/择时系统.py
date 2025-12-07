import akshare as ak
import pandas as pd
import numpy as np
import datetime

# ========== 1. 获取数据 ==========
today = datetime.date.today()
print(today)
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
hsgt_df = ak.stock_hsgt_hist_em(symbol="北向资金")
print(f"北向资金原始数据示例:\n{hsgt_df.head(3)}")
print(f"北向资金数据列名: {hsgt_df.columns.tolist()}")

# 检查数据总行数和日期范围
print(f"\n数据总行数: {len(hsgt_df)}")
print(f"日期范围: {hsgt_df['日期'].min()} 到 {hsgt_df['日期'].max()}")

# 检查最后几行的完整数据
print(f"\n最后10行完整数据:")
print(hsgt_df.tail(10).to_string())

# 检查"当日成交净买额"列是否有数据
if "当日成交净买额" in hsgt_df.columns:
    print(f"\n'当日成交净买额'最后5个值:")
    print(hsgt_df.tail(5)[['日期', '当日成交净买额', '当日资金流入']])
    print(f"'当日成交净买额'数据类型: {hsgt_df['当日成交净买额'].dtype}")
    print(f"'当日成交净买额'非空值数量: {hsgt_df['当日成交净买额'].notna().sum()}")

# 过滤掉NaN行，获取有效数据
hsgt_df_valid = hsgt_df.copy()
if "当日成交净买额" in hsgt_df_valid.columns:
    # 尝试使用"当日成交净买额"，过滤掉NaN行
    hsgt_df_valid = hsgt_df_valid[hsgt_df_valid['当日成交净买额'].notna()].copy()
    print(f"\n过滤后有效数据行数: {len(hsgt_df_valid)}")
    
    if len(hsgt_df_valid) > 0:
        # 使用有效数据计算
        hsgt_df_valid = hsgt_df_valid.tail(5)  # 最近5日有效数据
        hsgt_df_valid["当日资金流入"] = pd.to_numeric(hsgt_df_valid["当日成交净买额"], errors="coerce") / 10000  # 转换为亿元
        print(f"\n有效数据的最近5日:\n{hsgt_df_valid[['日期', '当日成交净买额', '当日资金流入']]}")
        north_inflow_5d = hsgt_df_valid["当日资金流入"].sum()  # 亿元
    else:
        print("警告: 没有找到有效数据，使用0")
        north_inflow_5d = 0
else:
    # 如果"当日成交净买额"不存在，尝试其他方法
    hsgt_df = hsgt_df.tail(5)  # 最近5日
    if "当日资金流入" in hsgt_df.columns:
        hsgt_df["当日资金流入"] = pd.to_numeric(hsgt_df["当日资金流入"], errors="coerce")
        # 如果全部是NaN，尝试使用"买入成交额"和"卖出成交额"计算
        if hsgt_df["当日资金流入"].isna().all():
            if "买入成交额" in hsgt_df.columns and "卖出成交额" in hsgt_df.columns:
                print("使用'买入成交额'和'卖出成交额'计算净流入...")
                buy = pd.to_numeric(hsgt_df["买入成交额"], errors="coerce")
                sell = pd.to_numeric(hsgt_df["卖出成交额"], errors="coerce")
                hsgt_df["当日资金流入"] = (buy - sell) / 10000  # 转换为亿元
        north_inflow_5d = hsgt_df["当日资金流入"].sum()  # 亿元
    else:
        north_inflow_5d = 0

print(f"\n最近5日北向资金净流入总和: {north_inflow_5d:.2f} 亿元")

# ========== 3. 涨停/跌停家数 ==========
print("\n=== 涨停跌停数据获取 ===")
try:
    # 优先使用东方财富接口
    spot_df = ak.stock_zh_a_spot_em()
    print(f"使用东方财富接口获取实时股票数据成功，共 {len(spot_df)}  股票")
except Exception as e1:
    print(f"东方财富接口获取失败: {e1}")
    try:
        # 备用方案：使用新浪接口
        spot_df = ak.stock_zh_a_spot()
        print(f"使用新浪接口获取实时股票数据成功，共 {len(spot_df)} 只股票")
    except Exception as e2:
        print(f"所有实时数据接口都失败: {e2}")
        # 如果都失败，使用默认值
        涨停数 = 0
        跌停数 = 0
        炸板率 = 0
        print("使用默认值: 涨停数=0, 跌停数=0, 炸板率=0")
        spot_df = pd.DataFrame()  # 空DataFrame

if not spot_df.empty:
    print(f"实时数据列名: {spot_df.columns.tolist()}")
    
    # 检查列名是否包含涨跌幅字段
    if '涨跌幅' in spot_df.columns:
        limit_up_df = spot_df[spot_df['涨跌幅'] >= 9.9]
        limit_down_df = spot_df[spot_df['涨跌幅'] <= -9.9]
        
        涨停数 = len(limit_up_df)
        跌停数 = len(limit_down_df)
        炸板率 = 0  # 实时数据无法获取炸板率，设置为0
        
        print(f"涨停股票数量: {涨停数}")
        print(f"跌停股票数量: {跌停数}")
        
        # 显示涨停股详情（如果有的话）
        if 涨停数 > 0:
            print(f"涨停股票示例:\n{limit_up_df[['代码', '名称', '涨跌幅']].head(5)}")
        if 跌停数 > 0:
            print(f"跌停股票示例:\n{limit_down_df[['代码', '名称', '涨跌幅']].head(5)}")
    else:
        print("数据中缺少'涨跌幅'列，使用默认值")
        涨停数 = 0
        跌停数 = 0
        炸板率 = 0

print(f"炸板率 (设置为0): {炸板率}")

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