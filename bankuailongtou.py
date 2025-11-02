import akshare as ak
import pandas as pd
# from datetime import datetime
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
# 设置中文字体
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False

# ====== 数据获取基础函数 ======
def get_index_data(symbol="sh000300", start_date="20240101", end_date=None):
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    df = ak.stock_zh_index_daily(symbol=symbol)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    return df[(df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))].reset_index()
def get_market_breadth():
    """获取赚钱效应，东方财富失败则用新浪数据"""
    try:
        # 东方财富接口
        spot_df = ak.stock_zh_a_spot_em()
        up_count = (spot_df["涨跌幅"] > 0).sum()
        total_stocks = len(spot_df)
        up_ratio = up_count / total_stocks
        limit_up_count = (spot_df["涨跌幅"] >= 9.9).sum()
        avg_gain = spot_df["涨跌幅"].mean()
        source = "东方财富"
    except Exception as e:
        print(f"   [警告] 东方财富接口失败：{e}")
        try:
            # 新浪接口备选
            spot_df = ak.stock_zh_a_spot()
            up_count = (spot_df["涨跌幅"] > 0).sum()
            total_stocks = len(spot_df)
            up_ratio = up_count / total_stocks
            limit_up_count = (spot_df["涨跌幅"] >= 9.9).sum()
            avg_gain = spot_df["涨跌幅"].mean()
            source = "新浪财经"
        except Exception as e2:
            return {"错误": f"东方财富和新浪接口都无法获取：{e2}"}
    
    return {
        "数据来源": source,
        "上涨家数占比": f"{up_ratio:.2%}",
        "涨停股数量": int(limit_up_count),
        "连板股数量": "需接入历史涨停接口计算",
        "市场平均涨幅": f"{avg_gain:.2f}%"
    }
def get_fund_concentration():
    try:
        # 东方财富板块数据
        industry_df = ak.stock_board_industry_name_em()
        source = "东方财富"
    except Exception as e:
        print(f"[警告] 东方财富接口失败：{e}")
        try:
            # 同花顺板块数据
            industry_df = ak.stock_board_industry_name_ths()
            source = "同花顺"
        except Exception as e2:
            return {"错误": f"板块数据获取失败：{e2}"}

    industry_top5 = industry_df.nlargest(5, "涨跌幅")[["板块名称", "涨跌幅"]].reset_index(drop=True)
    industry_top5["涨跌幅"] = industry_top5["涨跌幅"].astype(float).round(2).astype(str) + "%"
    
    return {
        "数据来源": source,
        "资金聚焦行业（当日涨幅前5）": industry_top5
    }
# def get_market_breadth():
#     """一次性获取赚钱效应（实时失败则用历史数据）"""
#     try:
#         # 实时行情（优先）
#         spot_df = ak.stock_zh_a_spot_em()
#         up_count = (spot_df["涨跌幅"] > 0).sum()
#         total_stocks = len(spot_df)
#         up_ratio = up_count / total_stocks
#         limit_up_count = (spot_df["涨跌幅"] >= 9.9).sum()
#         avg_gain = spot_df["涨跌幅"].mean()
#         return {
#             "上涨家数占比": f"{up_ratio:.2%}",
#             "涨停股数量": int(limit_up_count),
#             "连板股数量": "需接入历史涨停接口计算",
#             "市场平均涨幅": f"{avg_gain:.2f}% (实时数据)"
#         }
#     except Exception as e:
#         print(f"   [警告] 实时赚钱效应获取失败：{e}")
#         print("   [提示] 尝试使用历史收盘数据计算...")

#         try:
#             # 备用方案：历史数据
#             # 找最近一个交易日（防止周末/节假日）
#             date = datetime.now()
#             for _ in range(7):  # 最多回退7天
#                 date_str = date.strftime("%Y%m%d")
#                 try:
#                     hist_df = ak.stock_zh_a_hist(symbol="sz000001", period="daily",
#                                                  start_date=date_str, end_date=date_str)
#                     if not hist_df.empty:
#                         break
#                 except:
#                     pass
#                 date -= timedelta(days=1)

#             if hist_df.empty:
#                 return {"错误": "历史数据也无法获取"}
            
#             # 如果列名不同，处理涨跌幅
#             if "涨跌幅" not in hist_df.columns:
#                 change_cols = [col for col in hist_df.columns if "涨" in col and "幅" in col]
#                 if change_cols:
#                     hist_df.rename(columns={change_cols[0]: "涨跌幅"}, inplace=True)
#                 else:
#                     return {"错误": "找不到涨跌幅列"}

#             up_count = (hist_df["涨跌幅"] > 0).sum()
#             total_stocks = len(hist_df)
#             up_ratio = up_count / total_stocks
#             limit_up_count = (hist_df["涨跌幅"] >= 9.9).sum()
#             avg_gain = hist_df["涨跌幅"].mean()

#             return {
#                 "上涨家数占比": f"{up_ratio:.2%}",
#                 "涨停股数量": int(limit_up_count),
#                 "连板股数量": "需接入历史涨停接口计算",
#                 "市场平均涨幅": f"{avg_gain:.2f}% (最近交易日)"
#             }
#         except Exception as e2:
#             return {"错误": f"备用赚钱效应也获取失败：{e2}"}
        
# # def get_market_breadth():
#     """一次性获取赚钱效应"""
#     try:
#         spot_df = ak.stock_zh_a_spot_em()
#         up_count = (spot_df["涨跌幅"] > 0).sum()
#         total_stocks = len(spot_df)
#         up_ratio = up_count / total_stocks
#         limit_up_count = (spot_df["涨跌幅"] >= 9.9).sum()
#         avg_gain = spot_df["涨跌幅"].mean()
#         return {
#             "上涨家数占比": f"{up_ratio:.2%}",
#             "涨停股数量": int(limit_up_count),
#             "连板股数量": "需接入历史涨停接口计算",
#             "市场平均涨幅": f"{avg_gain:.2f}%"
#         }
#     except Exception as e:
#         return {"错误": f"赚钱效应获取失败：{str(e)}"}

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

# ====== 新增：热点板块和核心个股分析 ======
def get_hot_board_and_core():
    """获取热点板块里的 中军龙头 + 跟风股"""
    try:
        # 今日涨幅前3的板块
        boards = ak.stock_board_industry_name_em()
        hot_boards = boards.nlargest(3, "涨跌幅")[["板块名称", "涨跌幅"]]

        result = []
        for _, row in hot_boards.iterrows():
            board_name = row["板块名称"]
            # 获取板块成份股
            board_stocks = ak.stock_board_industry_cons_em(symbol=board_name)
            board_stocks = board_stocks.sort_values("涨跌幅", ascending=False).reset_index(drop=True)

            core_stock = board_stocks.iloc[0] if len(board_stocks) > 0 else None
            second_stock = board_stocks.iloc[1] if len(board_stocks) > 1 else None

            result.append({
                "板块": board_name,
                "板块涨幅": f"{row['涨跌幅']:.2f}%",
                "中军龙头": f"{core_stock['代码']} {core_stock['名称']} 涨幅:{core_stock['涨跌幅']:.2f}%" if core_stock is not None else "-",
                "跟风股": f"{second_stock['代码']} {second_stock['名称']} 涨幅:{second_stock['涨跌幅']:.2f}%" if second_stock is not None else "-",
                "套利机会": "是" if core_stock is not None and core_stock["涨跌幅"] > 3 else "否"
            })
        return result
    except Exception as e:
        return {"错误": f"板块分析获取失败：{str(e)}"}

# ====== 分析主类 ======
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

        # 1. 市场环境
        env, strategy, _ = self.judge_market_env()
        print(f"\n1. 市场大环境：{env}")
        print(f"   操作策略：{strategy}")

        # 2. 赚钱效应
        breadth_data = get_market_breadth()
        print(f"\n2. 赚钱效应：")
        for key, value in breadth_data.items():
            print(f"   - {key}：{value}")

        # 3. 风格表现
        style_df = get_style_performance(self.start_date, self.end_date)
        print(f"\n3. 赚钱风格（区间涨跌幅Top5）：")
        for idx, row in style_df.head(5).iterrows():
            print(f"   - {row['风格']}：{row['区间涨跌幅']}")

        # 4. 资金聚焦
        fund_data = get_fund_concentration()
        print(f"\n4. 资金聚焦：")
        if "错误" in fund_data:
            print(f"   - {fund_data['错误']}")
        else:
            print(f"   - 北向资金近5日净流入：{fund_data['北向资金近5日净流入（亿元）']} 亿元")
            print(f"   - 当日涨幅前5行业：")
            for idx, row in fund_data["资金聚焦行业（当日涨幅前5）"].iterrows():
                print(f"     {idx+1}. {row['板块名称']}：{row['涨跌幅']}")

        # 5. 板块&核心个股分析
        hot_data = get_hot_board_and_core()
        print("\n5. 热点板块及核心个股：")
        if isinstance(hot_data, dict) and "错误" in hot_data:
            print(f"   - {hot_data['错误']}")
        else:
            for b in hot_data:
                print(f"   - 板块: {b['板块']} 涨幅: {b['板块涨幅']}")
                print(f"     中军龙头: {b['中军龙头']}")
                print(f"     跟风股: {b['跟风股']}")
                print(f"     是否有套利机会: {b['套利机会']}")

# ====== 主运行入口 ======
if __name__ == "__main__":
    analysis = MarketAnalysisWithStyle(index_symbol="sh000001", start_date="20240101")
    analysis.run_full_analysis()