import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

# 设置中文显示
pd.set_option('display.max_columns', None)

# ================= 基础数据获取 =================
def get_index_data(symbol="sh000300", start_date="20240101", end_date=None):
    """获取指数行情数据"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    df = ak.stock_zh_index_daily(symbol=symbol)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    return df[(df.index >= pd.to_datetime(start_date)) &
              (df.index <= pd.to_datetime(end_date))].reset_index()

# ================= 赚钱效应 =================
def get_market_breadth():
    """东方财富失败则切新浪财经"""
    try:
        spot_df = ak.stock_zh_a_spot_em()
        source = "东方财富"
    except Exception as e:
        print(f"[警告] 东方财富接口失败：{e}")
        try:
            spot_df = ak.stock_zh_a_spot()
            source = "新浪财经"
        except Exception as e2:
            return {"错误": f"东方财富和新浪财经接口都失败：{e2}"}

    up_count = (spot_df["涨跌幅"] > 0).sum()
    total_stocks = len(spot_df)
    up_ratio = up_count / total_stocks
    limit_up_count = (spot_df["涨跌幅"] >= 9.9).sum()
    avg_gain = spot_df["涨跌幅"].mean()

    return {
        "数据来源": source,
        "上涨家数占比": f"{up_ratio:.2%}",
        "涨停股数量": int(limit_up_count),
        "连板股数量": "需接入历史涨停接口计算",
        "市场平均涨幅": f"{avg_gain:.2f}%"
    }

# ================= 风格表现 =================
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

# ================= 改进版资金聚焦 =================
def get_fund_concentration():
    """东方财富失败则切同花顺，并适配列名"""
    try:
        industry_df = ak.stock_board_industry_name_em()
        source = "东方财富"
    except Exception as e:
        print(f"[警告] 东方财富行业接口失败：{e}")
        try:
            industry_df = ak.stock_board_industry_name_ths()
            source = "同花顺"
        except Exception as e2:
            return {"错误": f"行业数据获取失败：{e2}"}

    if "涨跌幅" not in industry_df.columns:
        possible_cols = [col for col in industry_df.columns if "涨" in col and "幅" in col]
        if possible_cols:
            industry_df.rename(columns={possible_cols[0]: "涨跌幅"}, inplace=True)
        else:
            return {"错误": f"{source}接口数据无涨跌幅列"}

    industry_top5 = industry_df.nlargest(5, "涨跌幅")[["板块名称", "涨跌幅"]].drop_duplicates()
    industry_top5["涨跌幅"] = industry_top5["涨跌幅"].astype(float).round(2).astype(str) + "%"

    try:
        hsgt_df = ak.stock_hsgt_hist_em(symbol="北向资金").sort_values("日期", ascending=False).head(5)
        north_5d = hsgt_df["当日资金流入"].sum()
    except:
        north_5d = 0

    return {
        "数据来源": source,
        "资金聚焦行业（当日涨幅前5）": industry_top5,
        "北向资金近5日净流入（亿元）": round(north_5d / 10000, 2)
    }

# ================= 板块与核心个股 =================
def get_hot_board_and_core():
    try:
        boards = ak.stock_board_industry_name_em()
        source = "东方财富"
    except Exception as e:
        print(f"[警告] 东方财富板块接口失败：{e}")
        try:
            boards = ak.stock_board_industry_name_ths()
            source = "同花顺"
        except Exception as e2:
            return {"错误": f"板块数据获取失败：{e2}"}

    hot_boards = boards.nlargest(3, "涨跌幅")[["板块名称", "涨跌幅"]].drop_duplicates()
    result = []
    for _, row in hot_boards.iterrows():
        board_name = row["板块名称"]
        try:
            if source == "东方财富":
                board_stocks = ak.stock_board_industry_cons_em(symbol=board_name)
            else:
                board_stocks = ak.stock_board_industry_cons_ths(symbol=board_name)
        except Exception as e:
            return {"错误": f"成份股数据失败：{e}"}

        board_stocks = board_stocks.sort_values("涨跌幅", ascending=False).reset_index(drop=True)
        core_stock = board_stocks.iloc[0] if len(board_stocks) > 0 else None
        second_stock = board_stocks.iloc[1] if len(board_stocks) > 1 else None

        result.append({
            "数据来源": source,
            "板块": board_name,
            "板块涨幅": f"{row['涨跌幅']:.2f}%",
            "中军龙头": f"{core_stock['代码']} {core_stock['名称']} 涨幅:{core_stock['涨跌幅']:.2f}%" if core_stock is not None else "-",
            "跟风股": f"{second_stock['代码']} {second_stock['名称']} 涨幅:{second_stock['涨跌幅']:.2f}%" if second_stock is not None else "-",
            "套利机会": "是" if core_stock is not None and core_stock["涨跌幅"] > 3 else "否"
        })
    return result

# ================= 回测类 =================
class BacktestStrategy:
    def __init__(self, initial_cash=10000):
        self.cash = initial_cash
        self.positions = {}
        self.trade_history = []

    def market_signal(self, index_df):
        ma5 = index_df['close'].rolling(5).mean().iloc[-1]
        ma20 = index_df['close'].rolling(20).mean().iloc[-1]
        return "BUY" if ma5 > ma20 else "SELL"

    def get_stock_price(self, code, date):
        try:
            hist = ak.stock_zh_a_hist(symbol=code, period="daily",
                                      start_date=date, end_date=date)
            return float(hist.iloc[0]['收盘'])
        except:
            return None

    def buy(self, code, name, price, ratio=1.0):
        amount = self.cash * ratio
        shares = int(amount // price)
        self.cash -= shares * price
        self.positions[code] = {"name": name, "shares": shares, "buy_price": price}

    def sell(self, code, price):
        pos = self.positions.pop(code)
        self.cash += pos['shares'] * price
        profit = (price - pos['buy_price']) * pos['shares']
        self.trade_history.append(profit)

    def run_backtest(self, date_list):
        for date in date_list:
            idx_df = get_index_data("sh000001", start_date="20240101", end_date=date)
            if idx_df.empty:
                continue
            signal = self.market_signal(idx_df)

            if signal == "BUY" and not self.positions:
                board_df = ak.stock_board_industry_name_em()
                hot_industry = board_df.iloc[0]['板块名称']
                stocks = ak.stock_board_industry_cons_em(symbol=hot_industry)
                core = stocks.sort_values('涨跌幅', ascending=False).iloc[0]
                code, name = core['代码'], core['名称']
                price = self.get_stock_price(code, date)
                if price:
                    self.buy(code, name, price, ratio=1.0)

            elif signal == "SELL" and self.positions:
                for code in list(self.positions.keys()):
                    price = self.get_stock_price(code, date)
                    if price:
                        self.sell(code, price)

        win_rate = sum(1 for p in self.trade_history if p > 0) / len(self.trade_history) if self.trade_history else 0
        avg_win = (sum(p for p in self.trade_history if p > 0) / 
                   max(1, len([p for p in self.trade_history if p > 0])))
        avg_loss = abs(sum(p for p in self.trade_history if p < 0) / 
                       max(1, len([p for p in self.trade_history if p < 0])))
        odds_ratio = avg_win / avg_loss if avg_loss > 0 else None

        return {
            "最终资金": self.cash,
            "胜率": win_rate,
            "赔率": odds_ratio,
            "总交易次数": len(self.trade_history),
            "交易记录": self.trade_history
        }

# ================= 主运行入口 =================
if __name__ == "__main__":
    # 今日分析
    print(f"===== {datetime.now().strftime('%Y-%m-%d')} 市场全景分析 =====")
    env_df = get_index_data("sh000001", start_date="20240101")
    # 赚钱效应
    breadth = get_market_breadth()
    print("\n2. 赚钱效应：", breadth)

    # 资金聚焦
    fund = get_fund_concentration()
    print("\n4. 资金聚焦：", fund)

    # 热点板块
    hot = get_hot_board_and_core()
    print("\n5. 热点板块及核心个股：", hot)

    # 历史回测
    print("\n===== 历史回测 =====")
    backtest = BacktestStrategy(initial_cash=10000)
    date_list = [(datetime.now() - timedelta(days=i)).strftime("%Y%m%d") for i in range(250, 0, -1)]
    result = backtest.run_backtest(date_list)
    print(result)