

### 三、A股行情判定代码（`market_timing.py`）

import akshare as ak
import pandas as pd
import numpy as np
import datetime
from datetime import timedelta
import logging

# 配置日志（记录错误和运行信息）
logging.basicConfig(
    filename='market_timing.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class AShareTiming:
    def __init__(self, index_code="000300.SH"):
        """
        初始化A股市场择时工具
        index_code: 指数代码（沪深300:000300.SH；创业板指:399006.SZ；上证综指:000001.SH）
        """
        self.index_code = index_code
        self.index_name = self._get_index_name()  # 指数名称（用于输出）
        self.df = None  # 指数数据（含技术指标）
        self.profit_ratio = 0  # 赚钱效应（上涨个股占比）

    def _get_index_name(self):
        """获取指数名称（增强输出可读性）"""
        index_map = {
            "000300.SH": "沪深300",
            "399006.SZ": "创业板指",
            "000001.SH": "上证综指"
        }
        return index_map.get(self.index_code, "未知指数")

    def fetch_index_data(self, days=180):
        """获取指数历史数据（含收盘价、成交量），默认取180天数据"""
        try:
            end_date = datetime.date.today().strftime("%Y%m%d")
            start_date = (datetime.date.today() - timedelta(days=days)).strftime("%Y%m%d")
            # 获取指数日线数据
            self.df = ak.stock_zh_index_daily(symbol=self.index_code)
            # 筛选日期范围并转换格式
            self.df["date"] = pd.to_datetime(self.df["date"])
            self.df = self.df[(self.df["date"] >= start_date) & (self.df["date"] <= end_date)]
            self.df.set_index("date", inplace=True)
            logging.info(f"成功获取 {self.index_name} 数据，共 {len(self.df)} 条")
            return True
        except Exception as e:
            logging.error(f"获取指数数据失败：{str(e)}")
            print(f"错误：获取 {self.index_name} 数据失败，请检查网络或指数代码")
            return False

    def fetch_profit_ratio(self):
        """计算赚钱效应（全市场上涨个股占比）"""
        try:
            # 获取当日所有A股涨跌幅（深沪京市场）
            today = datetime.date.today().strftime("%Y-%m-%d")
            # 深市A股
            sz = ak.stock_zh_a_spot_em()
            # 沪市A股（包含主板和科创板）
            sh = ak.stock_zh_a_spot_em(board="沪市A股")
            # 合并数据并去重（避免重复计算）
            all_stocks = pd.concat([sz, sh], ignore_index=True).drop_duplicates(subset="代码")
            # 计算上涨个股数量
            up_stocks = all_stocks[all_stocks["涨跌幅"] > 0]
            self.profit_ratio = round(len(up_stocks) / len(all_stocks) * 100, 2)
            logging.info(f"赚钱效应计算完成：上涨个股占比 {self.profit_ratio}%")
            return True
        except Exception as e:
            # 非交易日或数据未更新时，使用昨日数据
            yesterday = (datetime.date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
            logging.warning(f"获取当日个股数据失败，尝试使用 {yesterday} 数据：{str(e)}")
            try:
                sz = ak.stock_zh_a_hist(symbol="", start_date=yesterday, end_date=yesterday)
                sh = ak.stock_zh_a_hist(symbol="", start_date=yesterday, end_date=yesterday, market="sh")
                all_stocks = pd.concat([sz, sh], ignore_index=True).drop_duplicates(subset="代码")
                up_stocks = all_stocks[all_stocks["涨跌幅"] > 0]
                self.profit_ratio = round(len(up_stocks) / len(all_stocks) * 100, 2)
                return True
            except Exception as e2:
                logging.error(f"获取昨日个股数据失败：{str(e2)}")
                print("错误：无法计算赚钱效应，请检查网络")
                return False

    def calculate_indicators(self):
        """计算技术指标：均线、MACD、成交量比率等"""
        if self.df is None:
            if not self.fetch_index_data():
                return False
        
        # 1. 均线指标（MA20/MA60/MA120）
        self.df["MA20"] = self.df["close"].rolling(window=20, min_periods=1).mean()
        self.df["MA60"] = self.df["close"].rolling(window=60, min_periods=1).mean()
        self.df["MA120"] = self.df["close"].rolling(window=120, min_periods=1).mean()
        
        # 2. MA60趋势（向上发散：最近10天MA60斜率为正）
        self.df["MA60_trend"] = self.df["MA60"].diff(10) > 0  # 10天内MA60是否上涨
        
        # 3. MACD指标
        self.df["EMA12"] = self.df["close"].ewm(span=12, adjust=False).mean()
        self.df["EMA26"] = self.df["close"].ewm(span=26, adjust=False).mean()
        self.df["DIFF"] = self.df["EMA12"] - self.df["EMA26"]
        self.df["DEA"] = self.df["DIFF"].ewm(span=9, adjust=False).mean()
        self.df["MACD"] = (self.df["DIFF"] - self.df["DEA"]) * 2
        
        # 4. 成交量比率（当前成交量/30天均值）
        self.df["vol_30mean"] = self.df["volume"].rolling(window=30, min_periods=1).mean()
        self.df["vol_ratio"] = self.df["volume"] / self.df["vol_30mean"]
        
        # 5. 指数震荡幅度（最近20天）
        self.df["oscillation_range"] = (self.df["high"].rolling(20).max() - self.df["low"].rolling(20).min()) / self.df["low"].rolling(20).min() * 100
        
        logging.info("技术指标计算完成")
        return True

    def check_macd_top_divergence(self):
        """检查是否出现MACD顶背离：指数创新高，MACD未创新高"""
        if len(self.df) < 20:
            return False  # 数据不足，无法判断
        recent = self.df.tail(20)
        # 指数最近高点
        index_high = recent["high"].max()
        index_high_date = recent[recent["high"] == index_high].index[-1]
        # 高点时的MACD
        macd_at_high = recent.loc[index_high_date, "MACD"]
        # 当前MACD
        current_macd = recent["MACD"].iloc[-1]
        # 当前指数是否创新高
        is_index_new_high = recent["high"].iloc[-1] >= index_high
        return is_index_new_high and current_macd < macd_at_high

    def judge_environment(self):
        """判定当前市场环境并返回策略建议"""
        # 确保数据和指标完整
        if not self.fetch_profit_ratio():
            return None
        if not self.calculate_indicators():
            return None
        
        latest = self.df.iloc[-1]  # 最新数据
        result = {
            "date": datetime.date.today().strftime("%Y-%m-%d"),
            "index": self.index_name,
            "environment": "",
            "position": "",
            "action": "",
            "risk": ""
        }

        # 1. 主升浪判定
        if (
            latest["close"] > latest["MA60"] and  # 指数在MA60上方
            latest["MA60_trend"] and  # MA60向上
            latest["MACD"] > 0 and  # MACD在零轴上方
            not self.check_macd_top_divergence() and  # 无顶背离
            latest["vol_ratio"] > 1.3 and  # 成交量超30%
            self.profit_ratio > 70  # 赚钱效应超70%
        ):
            result["environment"] = "主升浪"
            result["position"] = "100%（全仓）"
            result["action"] = "聚焦主线（政策/资金驱动板块），选择市值大、涨幅领先的核心龙头，不频繁换股"
            result["risk"] = "1. 过早止盈错过后续涨幅；2. 切换非主线股导致收益跑输；3. 忽视顶背离信号高位被套"

        # 2. 震荡向上判定
        elif (
            (latest["MA20"] < latest["close"] < latest["MA60"]) and  # 在MA20与MA60之间
            self.df["low"].tail(10).diff().mean() > 0 and  # 低点逐步抬高
            40 <= self.profit_ratio <= 60 and  # 赚钱效应40%-60%
            0.8 <= latest["vol_ratio"] <= 1.3  # 成交量无持续缩量
        ):
            result["environment"] = "震荡向上"
            result["position"] = "100%（全仓）"
            result["action"] = "分仓轮动，回调时买低位板块，上涨后切换未启动板块，不追高已涨板块"
            result["risk"] = "1. 追高轮动板块导致刚买就回调；2. 单一板块满仓错过其他机会；3. 误判为主升浪回调时扛单"

        # 3. 震荡行情判定
        elif (
            latest["oscillation_range"] <= 5 and  # 20天振幅≤5%
            20 <= self.profit_ratio <= 40 and  # 赚钱效应20%-40%
            latest["vol_ratio"] < 0.8  # 成交量缩量（低于均值20%）
        ):
            result["environment"] = "震荡行情"
            result["position"] = "50%（半仓）"
            result["action"] = "只参与主线龙头股，剩余仓位观望；无主线则仓位≤30%，不强行操作"
            result["risk"] = "1. 无主线时满仓分散买非核心股导致亏损；2. 主线结束未离场被套高位；3. 频繁交易侵蚀收益"

        # 4. 震荡向下判定
        elif (
            latest["close"] < latest["MA60"] and  # 指数在MA60下方
            self.df["high"].tail(10).diff().mean() < 0 and  # 高点逐步降低
            10 <= self.profit_ratio <= 20 and  # 赚钱效应10%-20%
            (latest["vol_ratio"] > 1.2 and self.df["vol_ratio"].iloc[-2] < 0.8)  # 反弹放量、回调缩量
        ):
            result["environment"] = "震荡向下"
            result["position"] = "≤20%（小仓）"
            result["action"] = "小仓参与超跌优质股反弹，设置严格止损（跌破反弹起点即卖），不恋战"
            result["risk"] = "1. 小仓变满仓导致反弹结束后深套；2. 不止损误把短期反弹当趋势反转；3. 抄底未超跌个股反弹力度弱"

        # 5. 单边向下判定
        elif (
            latest["close"] < latest["MA60"] and latest["close"] < latest["MA120"] and  # 跌破MA60、MA120
            self.profit_ratio < 10 and  # 赚钱效应<10%
            (latest["vol_ratio"] > 1.5 or latest["vol_ratio"] < 0.5)  # 放量下跌或缩量阴跌
        ):
            result["environment"] = "单边向下"
            result["position"] = "0%（空仓）"
            result["action"] = "坚决不进场，无论个股多便宜都不抄底；等待趋势反转信号（站稳MA60+放量）"
            result["risk"] = "1. 抄底看似低位个股导致持续阴跌深套；2. 误判反弹为反转进场被套；3. 空仓后忍不住追反弹反复亏损"

        # 指标冲突时的保守策略
        else:
            result["environment"] = "指标冲突（待确认）"
            result["position"] = "≤30%（保守仓位）"
            result["action"] = "观望为主，等待明确信号后再操作"
            result["risk"] = "市场信号混乱，操作易失误，建议减少交易频率"

        return result

    def print_result(self, result):
        """格式化输出判定结果"""
        if not result:
            print("无法生成判定结果，请检查日志文件")
            return
        print(f"\n===== {result['date']} {result['index']} 市场环境判定 =====")
        print(f"当前市场环境：{result['environment']}")
        print(f"建议仓位：{result['position']}")
        print(f"核心操作：{result['action']}")
        print(f"风险提示：{result['risk']}")
        print("=========================================\n")


if __name__ == "__main__":
    # 可切换指数：沪深300(000300.SH)、创业板指(399006.SZ)、上证综指(000001.SH)
    timing = AShareTiming(index_code="000300.SH")
    # 执行判定
    result = timing.judge_environment()
    # 输出结果
    timing.print_result(result)