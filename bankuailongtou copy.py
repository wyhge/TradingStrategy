import tushare as ts
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import time
import warnings
warnings.filterwarnings("ignore")

# ====== Tushare初始化（必须配置token）======
TUSHARE_TOKEN = "6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9"  # 替换为你的实际token
pro = ts.pro_api(TUSHARE_TOKEN)

# 基础设置（解决中文显示问题）
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False

# 全局配置
A股_MARKET = ["SH", "SZ", "BJ"]  # 沪深京市场
INDEX_MAPPING = {  # 指数代码映射（tushare格式：指数代码.SH/SZ）
    "sh000001": "000001.SH",  # 上证指数
    "sh000300": "000300.SH",  # 沪深300
    "sh000905": "000905.SH",  # 中证500
    "sh000852": "000852.SH",  # 中证1000
    "sz399006": "399006.SZ",  # 创业板指
    "sh000015": "000015.SH",  # 大盘价值
    "sh000016": "000016.SH",  # 大盘成长
    "sh000017": "000017.SH",  # 中盘价值
    "sh000018": "000018.SH",  # 中盘成长
    "sh000019": "000019.SH",  # 小盘价值
    "sh000020": "000020.SH"   # 小盘成长
}
STYLE_INDEXES = {  # 风格指数配置（名称：tushare指数代码）
    "大盘价值": "000015.SH",
    "大盘成长": "000016.SH",
    "中盘价值": "000017.SH",
    "中盘成长": "000018.SH",
    "小盘价值": "000019.SH",
    "小盘成长": "000020.SH",
    "沪深300（大盘）": "000300.SH",
    "中证500（中盘）": "000905.SH",
    "中证1000（小盘）": "000852.SH",
    "创业板指（成长）": "399006.SZ"
}


# ====== 工具函数：代码格式转换（akshare→tushare）======
def convert_code(ak_code: str) -> str:
    """将akshare格式代码（sh000001）转为tushare格式（000001.SH）"""
    if ak_code.startswith("sh"):
        return f"{ak_code[2:]}.SH"
    elif ak_code.startswith("sz"):
        return f"{ak_code[2:]}.SZ"
    elif ak_code.startswith("bj"):
        return f"{ak_code[2:]}.BJ"
    return ak_code


# ====== 指数数据获取（tushare替换）======
def get_index_data(symbol="sh000001", start_date="20240101", end_date=None):
    """获取指数日频数据（tushare.pro.index_daily）"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    # 转换指数代码
    ts_code = INDEX_MAPPING.get(symbol, convert_code(symbol))
    try:
        # 调用tushare指数日频接口
        df = pro.index_daily(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )
        # 格式处理（和原代码保持一致）
        df["date"] = pd.to_datetime(df["trade_date"])
        df = df.rename(columns={
            "open": "open", "close": "close", "high": "high",
            "low": "low", "vol": "volume"
        })
        df = df[["date", "open", "close", "high", "low", "volume"]].set_index("date").reset_index()
        return df
    except Exception as e:
        print(f"[警告] 指数{symbol}获取失败：{str(e)[:50]}...")
        return pd.DataFrame(columns=["date", "open", "close", "high", "low", "volume"])


# ====== A股实时行情（tushare替换，批量获取）======
def get_a_share_realtime() -> pd.DataFrame:
    """批量获取所有A股实时行情（tushare.pro.realtime_quotes）"""
    all_stocks = []
    # 1. 获取所有A股代码
    try:
        stock_basic = pro.stock_basic(list_status="L", exchange="")  # 所有上市A股
        stock_codes = stock_basic["ts_code"].tolist()
    except Exception as e:
        print(f"[警告] 获取A股列表失败：{e}")
        return pd.DataFrame()
    
    # 2. 分批获取实时行情（tushare一次最多300个代码）
    batch_size = 300
    for i in range(0, len(stock_codes), batch_size):
        batch_codes = stock_codes[i:i+batch_size]
        try:
            df = pro.realtime_quotes(ts_code=",".join(batch_codes))
            all_stocks.append(df)
            time.sleep(0.5)  # 控制请求频率
        except Exception as e:
            print(f"[警告] 批量{str(i)}-{str(i+batch_size)}股票行情获取失败：{e}")
            continue
    
    if not all_stocks:
        return pd.DataFrame()
    # 合并数据并处理格式
    result_df = pd.concat(all_stocks, ignore_index=True)
    result_df["涨跌幅"] = pd.to_numeric(result_df["changepercent"], errors="coerce")
    result_df["最新价"] = pd.to_numeric(result_df["price"], errors="coerce")
    result_df["代码"] = result_df["ts_code"].str.split(".").str[0] + "." + result_df["ts_code"].str.split(".").str[1].str.lower()
    result_df["名称"] = result_df["name"]
    return result_df[["代码", "名称", "最新价", "涨跌幅"]]


# ====== 赚钱效应（基于tushare实时行情计算）======
def get_market_breadth():
    """赚钱效应：上涨家数占比、涨停股数量等（tushare数据）"""
    try:
        spot_df = get_a_share_realtime()
        if spot_df.empty:
            raise Exception("实时行情数据为空")
        
        total_stocks = len(spot_df)
        up_count = (spot_df["涨跌幅"] > 0).sum()
        up_ratio = up_count / total_stocks if total_stocks > 0 else 0
        # 涨停股（涨跌幅≥9.9%）
        limit_up_count = (spot_df["涨跌幅"] >= 9.9).sum()
        avg_gain = spot_df["涨跌幅"].mean() if total_stocks > 0 else 0
        
        return {
            "数据来源": "tushare实时行情",
            "上涨家数占比": f"{up_ratio:.2%}",
            "涨停股数量": int(limit_up_count),
            "连板股数量": "需接入历史涨停接口计算",
            "市场平均涨幅": f"{avg_gain:.2f}%"
        }
    except Exception as e:
        print(f"[警告] 赚钱效应计算失败：{str(e)[:50]}...")
        return {
            "数据来源": "tushare接口不可用",
            "上涨家数占比": "无法获取",
            "涨停股数量": "无法获取",
            "连板股数量": "无法获取",
            "市场平均涨幅": "无法获取"
        }


# ====== 资金聚焦（tushare行业数据+北向资金）======
def get_fund_concentration():
    """资金聚焦：行业涨跌幅+北向资金（tushare替换）"""
    # 1. 行业涨跌幅（tushare.pro.industry_daily）
    industry_df = pd.DataFrame(columns=["板块名称", "涨跌幅"])
    source_industry = "无"
    try:
        # 获取申万一级行业日频数据（最新交易日）
        latest_date = datetime.now().strftime("%Y%m%d")
        industry_daily = pro.industry_daily(
            ts_code="", 
            trade_date=latest_date,
            src="SW"  # 申万行业分类
        )
        # 格式处理
        industry_df = industry_daily.rename(columns={
            "industry_name": "板块名称",
            "pct_change": "涨跌幅"
        })[["板块名称", "涨跌幅"]]
        source_industry = "tushare申万行业"
    except Exception as e:
        print(f"[警告] 行业数据获取失败：{str(e)[:50]}...")
        # 备用：手动填充默认数据
        industry_df = pd.DataFrame({
            "板块名称": ["无法获取行业数据", "请检查tushare权限", "或稍后重试"],
            "涨跌幅": [0.0, 0.0, 0.0]
        })
    
    # 2. 北向资金（沪深港通资金流向，近5日）
    north_5d = "无法获取"
    source_north = "无"
    try:
        # 获取近5个交易日的北向资金净流入
        end_date = datetime.now().strftime("%Y%m%d")
        hsgt_df = pro.hsgt_capital_flow(
            start_date=pd.date_range(end=end_date, periods=7).strftime("%Y%m%d").tolist()[0],
            end_date=end_date
        )
        # 计算近5日净流入（亿元）
        hsgt_df["north_net"] = pd.to_numeric(hsgt_df["north_money"], errors="coerce")
        north_5d = hsgt_df["north_net"].sum() / 10000  # 转换为亿元
        source_north = "tushare沪深港通数据"
    except Exception as e:
        print(f"[警告] 北向资金获取失败：{e}")
    
    # 行业涨跌幅格式化
    industry_df["涨跌幅"] = pd.to_numeric(industry_df["涨跌幅"], errors="coerce").fillna(0.0)
    industry_top5 = industry_df.nlargest(5, "涨跌幅")[["板块名称", "涨跌幅"]].reset_index(drop=True)
    industry_top5["涨跌幅"] = industry_top5["涨跌幅"].apply(lambda x: f"{x:.2f}%" if x != 0 else "-")

    return {
        "行业数据来源": source_industry,
        "北向资金来源": source_north,
        "资金聚焦行业（当日涨幅前5）": industry_top5,
        "北向资金近5日净流入（亿元）": round(north_5d, 2) if isinstance(north_5d, float) else north_5d
    }


# ====== 风格表现（tushare风格指数计算）======
def get_style_performance(start_date="20240101", end_date=None):
    """风格指数区间涨跌幅（tushare替换）"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    out_list = []
    
    for name, ts_code in STYLE_INDEXES.items():
        try:
            # 获取风格指数日频数据
            df = pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if len(df) < 2:
                continue
            # 计算区间涨跌幅
            start_close = df.iloc[0]["close"]
            end_close = df.iloc[-1]["close"]
            gain = (end_close - start_close) / start_close
            out_list.append({"风格": name, "区间涨跌幅": f"{gain:.2%}"})
        except Exception as e:
            print(f"[警告] 风格指数{name}获取失败：{str(e)[:30]}...")
            continue
    
    if not out_list:
        return pd.DataFrame([{"风格": "无法获取数据", "区间涨跌幅": "-"}])
    return pd.DataFrame(out_list).sort_values("区间涨跌幅", ascending=False)


# ====== 热点板块及核心个股（tushare行业成分股）======
def get_hot_board_and_core():
    """热点板块及核心个股（tushare行业成分股）"""
    try:
        # 1. 获取涨幅前3的行业
        latest_date = datetime.now().strftime("%Y%m%d")
        industry_daily = pro.industry_daily(trade_date=latest_date, src="SW")
        industry_daily["pct_change"] = pd.to_numeric(industry_daily["pct_change"], errors="coerce")
        hot_industries = industry_daily.nlargest(3, "pct_change")[["industry_name", "pct_change"]]
        result = []
        
        for _, row in hot_industries.iterrows():
            industry_name = row["industry_name"]
            industry_gain = row["pct_change"]
            try:
                # 2. 获取该行业的成分股
                stock_basic = pro.stock_basic(list_status="L")
                # 假设行业名称匹配（实际可通过pro.industry_classify获取精准成分股）
                industry_stocks = stock_basic[stock_basic["industry"] == industry_name]["ts_code"].tolist()
                if not industry_stocks:
                    raise Exception("无成分股数据")
                
                # 3. 获取成分股实时行情
                stock_quotes = pro.realtime_quotes(ts_code=",".join(industry_stocks[:300]))  # 限制300个
                stock_quotes["涨跌幅"] = pd.to_numeric(stock_quotes["changepercent"], errors="coerce")
                stock_quotes = stock_quotes.sort_values("涨跌幅", ascending=False).reset_index(drop=True)
            except Exception as e:
                print(f"[警告] 板块{industry_name}成分股失败：{e}")
                stock_quotes = pd.DataFrame(columns=["ts_code", "name", "changepercent"])
            
            # 提取龙头股
            core_stock = stock_quotes.iloc[0] if len(stock_quotes) > 0 else None
            second_stock = stock_quotes.iloc[1] if len(stock_quotes) > 1 else None
            
            result.append({
                "板块": industry_name,
                "板块涨幅": f"{industry_gain:.2f}%" if pd.notna(industry_gain) else "-",
                "中军龙头": f"{core_stock['ts_code']} {core_stock['name']} 涨幅:{core_stock['涨跌幅']:.2f}%" 
                            if core_stock is not None else "无数据",
                "跟风股": f"{second_stock['ts_code']} {second_stock['name']} 涨幅:{second_stock['涨跌幅']:.2f}%" 
                          if second_stock is not None else "无数据",
                "套利机会": "是" if (core_stock is not None and core_stock["涨跌幅"] > 3) else "否"
            })
        return result if result else [{"板块": "无热点板块", "板块涨幅": "-", "中军龙头": "-", "跟风股": "-", "套利机会": "-"}]
    except Exception as e:
        print(f"[警告] 热点板块获取失败：{e}")
        return [{"板块": "无法获取板块数据", "板块涨幅": "-", "中军龙头": "-", "跟风股": "-", "套利机会": "-"}]


# ====== 市场分析主类（逻辑不变，仅替换数据来源）======
class MarketAnalysisWithStyle:
    def __init__(self, index_symbol="sh000001", start_date="20240101", end_date=None):
        self.index_symbol = index_symbol
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.now().strftime("%Y%m%d")
        self.short_period = 20  # 短期均线
        self.long_period = 60   # 长期均线
        self.volatility_period = 20  # 波动率计算周期
        self.trend_threshold = 0.03  # 趋势强度阈值
        self.volatility_threshold = 0.05  # 波动率阈值

    def judge_market_env(self):
        """判断市场环境（逻辑不变）"""
        df = get_index_data(self.index_symbol, self.start_date, self.end_date)
        if len(df) < self.long_period:
            return "数据不足", "请扩大时间范围或检查指数代码", df
        
        # 计算均线和波动率
        df["pct_chg"] = df["close"].pct_change() * 100
        df[f"ma{self.short_period}"] = df["close"].rolling(self.short_period).mean()
        df[f"ma{self.long_period}"] = df["close"].rolling(self.long_period).mean()
        df = df.dropna()

        if df.empty:
            return "数据异常", "无法计算市场环境", df
        
        latest = df.iloc[-1]
        recent = df.iloc[-self.volatility_period:]
        short_above_long = latest[f"ma{self.short_period}"] > latest[f"ma{self.long_period}"]
        trend_strength = recent["pct_chg"].sum() / 100  # 趋势强度
        volatility = recent["pct_chg"].std() / 100  # 波动率

        # 判断市场环境
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
        """运行完整市场分析"""
        print(f"===== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 市场全景分析（tushare版）======")
        print("⚠️  注意：需确保tushare token有效，且已安装最新版tushare（pip install -U tushare）\n")

        # 1. 市场大环境
        env, strategy, _ = self.judge_market_env()
        print(f"1. 市场大环境：{env}")
        print(f"   操作策略：{strategy}\n")

        # 2. 赚钱效应
        breadth_data = get_market_breadth()
        print("2. 赚钱效应：")
        for key, value in breadth_data.items():
            print(f"   - {key}：{value}")
        print()

        # 3. 赚钱风格
        style_df = get_style_performance(self.start_date, self.end_date)
        print("3. 赚钱风格（区间涨跌幅Top5）：")
        for idx, row in style_df.head(5).iterrows():
            print(f"   - {row['风格']}：{row['区间涨跌幅']}")
        print()

        # 4. 资金聚焦
        fund_data = get_fund_concentration()
        print("4. 资金聚焦：")
        print(f"   - 北向资金近5日净流入：{fund_data['北向资金近5日净流入（亿元）']} 亿元")
        print(f"   - 当日涨幅前5行业：")
        for idx, row in fund_data["资金聚焦行业（当日涨幅前5）"].iterrows():
            print(f"     {idx+1}. {row['板块名称']}：{row['涨跌幅']}")
        print()

        # 5. 热点板块及核心个股
        hot_data = get_hot_board_and_core()
        print("5. 热点板块及核心个股：")
        for b in hot_data:
            print(f"   - 板块: {b['板块']} 涨幅: {b['板块涨幅']}")
            print(f"     中军龙头: {b['中军龙头']}")
            print(f"     跟风股: {b['跟风股']}")
            print(f"     是否有套利机会: {b['套利机会']}")
        print("\n===== 分析结束 =====")


# ====== 主运行入口 ======
if __name__ == "__main__":
    # 1. 配置tushare token（必须替换为你的实际token！）
    # TUSHARE_TOKEN = "你的tushare token"  # 请在此处替换，或在上方配置
    
    # 2. 运行分析（可自定义指数代码和起始日期）
    analysis = MarketAnalysisWithStyle(index_symbol="sh000001", start_date="20240101")
    analysis.run_full_analysis()