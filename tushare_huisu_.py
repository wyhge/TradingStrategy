
import tushare as ts
import pandas as pd
from datetime import datetime, timedelta
import time

# TuShare 配置（替换成你的 Token）
TOKEN = '6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9'
pro = ts.pro_api(TOKEN)
pd.set_option('display.max_columns', None)

# ================= 工具函数：获取最近有效交易日 =================
def get_latest_trade_date(max_lookback=10):
    today = datetime.now()
    for i in range(max_lookback):
        date_str = (today - timedelta(days=i)).strftime("%Y%m%d")
        df = safe_api_call(pro.daily, trade_date=date_str)
        if not df.empty:
            return date_str
    return None

# ================= 安全调用接口（加延时+重试） =================
def safe_api_call(func, *args, retries=3, delay=0.3, **kwargs):
    """封装TuShare接口调用，增加延时和失败重试"""
    for i in range(retries):
        try:
            time.sleep(delay)
            return func(*args, **kwargs)
        except Exception as e:
            print(f"[警告] 第 {i+1} 次调用 {func.__name__} 失败：{e}")
            time.sleep(delay * 2)
    return pd.DataFrame()

# ================= 获取指数行情 =================
def get_index_data(symbol='000001.SH', start_date="20240101", end_date=None):
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    df = safe_api_call(pro.index_daily, ts_code=symbol, start_date=start_date, end_date=end_date)
    if df.empty:
        return df
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    return df.sort_values('trade_date')

# ================= 赚钱效应 =================
def get_market_breadth(trade_date=None):
    if trade_date is None:
        trade_date = get_latest_trade_date()
    if not trade_date:
        return {"错误": "找不到最近的交易日"}

    df = safe_api_call(pro.daily, trade_date=trade_date)
    if df.empty:
        return {"错误": f"{trade_date} 没有股票行情数据"}

    up_count = (df['pct_chg'] > 0).sum()
    total = len(df)
    up_ratio = up_count / total if total else 0
    limit_up_df = df[df['pct_chg'] >= 9.9]
    limit_up_count = len(limit_up_df)

    # 连板股数量计算
    consecutive_limit_up = 0
    for ts_code in limit_up_df['ts_code']:
        hist = safe_api_call(pro.daily, ts_code=ts_code, end_date=trade_date)
        hist = hist.sort_values('trade_date', ascending=False).head(5)
        streak = 0
        for pct in hist['pct_chg']:
            if pct >= 9.9:
                streak += 1
            else:
                break
        if streak >= 2:
            consecutive_limit_up += 1

    avg_gain = df['pct_chg'].mean()
    return {
        "数据来源": "TuShare",
        "交易日": trade_date,
        "上涨家数占比": f"{up_ratio:.2%}",
        "涨停股数量": int(limit_up_count),
        "连板股数量": int(consecutive_limit_up),
        "市场平均涨幅": f"{avg_gain:.2f}%"
    }

# ================= 风格表现 =================
def get_style_performance(start_date="20240101", end_date=None):
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    style_indexes = {
        "沪深300": "000300.SH",
        "中证500": "000905.SH",
        "中证1000": "000852.SH",
        "创业板指": "399006.SZ"
    }
    data_out = []
    for name, ts_code in style_indexes.items():
        df = get_index_data(ts_code, start_date=start_date, end_date=end_date)
        if len(df) < 2:
            continue
        gain = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]
        data_out.append({"风格": name, "区间涨跌幅": f"{gain:.2%}"})
    return pd.DataFrame(data_out).sort_values("区间涨跌幅", ascending=False)

# ================= 改进版资金聚焦（快速版+限流+退路） =================
def get_fund_concentration(trade_date=None):
    if trade_date is None:
        trade_date = get_latest_trade_date()
    if not trade_date:
        return {"错误": "找不到最近的交易日"}

    df_daily = safe_api_call(pro.daily, trade_date=trade_date)
    if df_daily.empty:
        return {"错误": f"{trade_date} 没有市场行情数据"}

    df_company = safe_api_call(pro.stock_company, exchange='')

    # 情况1：有行业列 —— 正常模式
    if not df_company.empty and 'industry' in df_company.columns:
        df_merge = df_daily.merge(df_company[['ts_code', 'industry']], on='ts_code', how='left')
        df_merge = df_merge.dropna(subset=['industry'])
        industry_avg = (
            df_merge.groupby('industry')['pct_chg']
            .mean().reset_index()
            .rename(columns={'industry': '行业名称', 'pct_chg': '涨跌幅'})
        )
        top5 = industry_avg.sort_values('涨跌幅', ascending=False).head(5)
        top5['涨跌幅'] = top5['涨跌幅'].round(2).astype(str) + '%'
        return {
            "数据来源": "TuShare",
            "交易日": trade_date,
            "资金聚焦行业（涨幅前5）": top5.reset_index(drop=True)
        }
    else:
        # 情况2：无行业列 —— 退路模式
        top_stocks = df_daily.sort_values('pct_chg', ascending=False).head(30)

        # 获取股票基础信息以加上名称列
        df_basic = safe_api_call(pro.stock_basic, exchange='', fields='ts_code,name')
        if not df_basic.empty:
            top_stocks = top_stocks.merge(df_basic, on='ts_code', how='left')
        else:
            # 如果基础信息接口也无法获取，就只返回代码和涨幅
            top_stocks['name'] = '未知名称'

        return {
            "数据来源": "TuShare（无行业数据）",
            "交易日": trade_date,
            "资金聚焦股票池（涨幅前30）": top_stocks[['ts_code', 'name', 'pct_chg']].reset_index(drop=True)
        }

# ================= 热点板块及核心个股 =================
def get_hot_board_and_core(trade_date=None):
    if trade_date is None:
        trade_date = get_latest_trade_date()
    fund_data = get_fund_concentration(trade_date)
    if "资金聚焦行业（涨幅前5）" in fund_data:
        industries = fund_data["资金聚焦行业（涨幅前5）"]
        result = []
        df_daily = safe_api_call(pro.daily, trade_date=trade_date)
        df_company = safe_api_call(pro.stock_company, exchange='')
        if 'industry' in df_company.columns:
            df_merge = df_daily.merge(df_company[['ts_code', 'industry']], on='ts_code', how='left')
        else:
            return {"错误": "无行业数据无法获取热点板块"}
        for _, row in industries.iterrows():
            industry_name = row["行业名称"]
            sector_stocks = df_merge[df_merge['industry'] == industry_name]
            if not sector_stocks.empty:
                core = sector_stocks.sort_values('pct_chg', ascending=False).iloc[0]
                second = sector_stocks.sort_values('pct_chg', ascending=False).iloc[1] if len(sector_stocks) > 1 else None
                result.append({
                    "板块": industry_name,
                    "板块涨幅": row["涨跌幅"],
                    "中军龙头": f"{core['ts_code']} 涨幅:{core['pct_chg']:.2f}%",
                    "跟风股": f"{second['ts_code']} 涨幅:{second['pct_chg']:.2f}%" if second is not None else "-",
                    "套利机会": "是" if core['pct_chg'] > 3 else "否"
                })
        return {"交易日": trade_date, "热点板块": result}
    elif "资金聚焦股票池（涨幅前30）" in fund_data:
        return {"交易日": trade_date, "热点股票池": fund_data["资金聚焦股票池（涨幅前30）"]}
    else:
        return {"错误": "无法获取热点板块数据"}

# ================= 主运行入口 =================
if __name__ == "__main__":
    today_trade_date = get_latest_trade_date()
    print(f"===== {today_trade_date} 市场全景分析 =====")
    print("\n2. 赚钱效应：", get_market_breadth(today_trade_date))
    print("\n3. 风格表现：")
    print(get_style_performance("20240101", today_trade_date))
    print("\n4. 资金聚焦：", get_fund_concentration(today_trade_date))
    print("\n5. 热点板块及核心个股：", get_hot_board_and_core(today_trade_date))