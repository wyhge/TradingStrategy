import akshare as ak
import pandas as pd
import numpy as np
import datetime
import os


class DataFetcher:
    """数据获取类，负责从各种数据源获取市场数据"""
    
    def __init__(self, csv_path="北向资金数据.csv"):
        """
        初始化数据获取类
        
        Args:
            csv_path: 北向资金数据CSV文件路径
        """
        self.today = datetime.date.today()
        self.csv_path = csv_path
    
    def get_index_data(self, symbol="sh000300", days=60):
        """
        获取指数数据并计算技术指标
        
        Args:
            symbol: 指数代码
            days: 获取最近多少天的数据
            
        Returns:
            DataFrame: 包含技术指标的指数数据
        """
        index_df = ak.stock_zh_index_daily(symbol=symbol)
        index_df['date'] = pd.to_datetime(index_df['date'])
        index_df.sort_values("date", inplace=True)
        
        df = index_df.tail(days).copy()
        
        # 移动平均线
        df['MA5'] = df['close'].rolling(5).mean()
        df['MA20'] = df['close'].rolling(20).mean()
        df['MA60'] = df['close'].rolling(60).mean()
        df['MA5_slope'] = df['MA5'].diff()
        df['MA20_slope'] = df['MA20'].diff()
        
        # 成交量指标
        df['VOL_MA5'] = df['volume'].rolling(5).mean()
        df['VOL_MA20'] = df['volume'].rolling(20).mean()
        df['量比'] = df['volume'] / df['VOL_MA20']
        
        # 波动率
        df['Volatility'] = df['close'].rolling(20).std()
        
        # 涨跌幅
        df['涨跌幅'] = df['close'].pct_change()
        
        return df
    
    def get_northbound_capital(self, days=5):
        """
        获取北向资金数据
        优先从akshare获取，失败则从CSV文件读取
        
        Args:
            days: 获取最近多少天的数据
            
        Returns:
            float: 最近N日北向资金净流入总和（亿元）
        """
        print("=== 北向资金数据获取 ===")
        
        # 首先尝试从akshare获取
        try:
            hsgt_df = ak.stock_hsgt_hist_em(symbol="北向资金")
            hsgt_df = hsgt_df.sort_values("日期", ascending=False).head(days)
            
            # 优先使用"当日成交净买额"
            if "当日成交净买额" in hsgt_df.columns:
                hsgt_df["当日资金流入"] = pd.to_numeric(
                    hsgt_df["当日成交净买额"], errors="coerce"
                ) / 10000  # 万元转亿元
            elif "当日资金流入" in hsgt_df.columns:
                hsgt_df["当日资金流入"] = pd.to_numeric(
                    hsgt_df["当日资金流入"], errors="coerce"
                )
            else:
                # 使用买入和卖出计算
                if "买入成交额" in hsgt_df.columns and "卖出成交额" in hsgt_df.columns:
                    buy = pd.to_numeric(hsgt_df["买入成交额"], errors="coerce")
                    sell = pd.to_numeric(hsgt_df["卖出成交额"], errors="coerce")
                    hsgt_df["当日资金流入"] = (buy - sell) / 10000
                else:
                    hsgt_df["当日资金流入"] = 0
            
            north_inflow = hsgt_df["当日资金流入"].sum()
            
            # 如果获取成功且数据有效，尝试保存到CSV（用于后续备用）
            if not pd.isna(north_inflow) and north_inflow != 0:
                try:
                    self._save_to_csv(hsgt_df)
                except Exception as save_error:
                    print(f"保存数据到CSV失败（不影响使用）: {save_error}")
            
            print(f"从akshare获取成功，最近{days}日北向资金净流入总和: {north_inflow:.2f} 亿元")
            return north_inflow
            
        except Exception as e:
            print(f"从akshare获取北向资金数据失败: {e}")
            print("尝试从CSV文件读取...")
            
            # 从CSV文件读取备用数据
            try:
                return self._read_from_csv(days)
            except Exception as csv_error:
                print(f"从CSV文件读取也失败: {csv_error}")
                print("使用默认值: 0")
                return 0
    
    def _read_from_csv(self, days=5):
        """
        从CSV文件读取北向资金数据
        
        Args:
            days: 获取最近多少天的数据
            
        Returns:
            float: 最近N日北向资金净流入总和（亿元）
        """
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"CSV文件不存在: {self.csv_path}")
        
        # 读取CSV文件
        csv_df = pd.read_csv(self.csv_path, encoding="utf-8-sig")
        
        # 检查必要的列是否存在
        if "日期" not in csv_df.columns:
            raise ValueError("CSV文件中缺少'日期'列")
        
        # 转换日期列为日期类型
        csv_df["日期"] = pd.to_datetime(csv_df["日期"])
        csv_df = csv_df.sort_values("日期", ascending=False)
        
        # 获取最近N天的数据
        csv_df = csv_df.head(days)
        
        # 尝试不同的列名来获取资金流入数据
        inflow_col = None
        if "当日资金流入" in csv_df.columns:
            inflow_col = "当日资金流入"
        elif "当日成交净买额" in csv_df.columns:
            inflow_col = "当日成交净买额"
            # 如果是净买额（万元），需要转换为亿元
            csv_df["当日资金流入"] = pd.to_numeric(
                csv_df["当日成交净买额"], errors="coerce"
            ) / 10000
            inflow_col = "当日资金流入"
        elif "买入成交额" in csv_df.columns and "卖出成交额" in csv_df.columns:
            buy = pd.to_numeric(csv_df["买入成交额"], errors="coerce")
            sell = pd.to_numeric(csv_df["卖出成交额"], errors="coerce")
            csv_df["当日资金流入"] = (buy - sell) / 10000
            inflow_col = "当日资金流入"
        else:
            raise ValueError("CSV文件中找不到可用的资金流入数据列")
        
        # 计算总和
        north_inflow = pd.to_numeric(csv_df[inflow_col], errors="coerce").sum()
        
        if pd.isna(north_inflow):
            north_inflow = 0
        
        print(f"从CSV文件读取成功，最近{days}日北向资金净流入总和: {north_inflow:.2f} 亿元")
        return north_inflow
    
    def _save_to_csv(self, hsgt_df):
        """
        将北向资金数据保存到CSV文件
        
        Args:
            hsgt_df: 包含北向资金数据的DataFrame
        """
        # 选择要保存的列
        save_columns = ["日期"]
        
        # 优先保存"当日成交净买额"，如果没有则保存"当日资金流入"
        if "当日成交净买额" in hsgt_df.columns:
            save_columns.append("当日成交净买额")
        elif "当日资金流入" in hsgt_df.columns:
            save_columns.append("当日资金流入")
        elif "买入成交额" in hsgt_df.columns and "卖出成交额" in hsgt_df.columns:
            save_columns.extend(["买入成交额", "卖出成交额"])
        
        save_df = hsgt_df[save_columns].copy()
        
        # 如果文件已存在，读取现有数据并合并
        if os.path.exists(self.csv_path):
            existing_df = pd.read_csv(self.csv_path, encoding="utf-8-sig")
            existing_df["日期"] = pd.to_datetime(existing_df["日期"])
            
            # 合并数据，去重（保留新数据）
            combined_df = pd.concat([existing_df, save_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=["日期"], keep="last")
            combined_df = combined_df.sort_values("日期", ascending=False)
        else:
            combined_df = save_df.sort_values("日期", ascending=False)
        
        # 保存到CSV
        combined_df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
        print(f"数据已保存到: {self.csv_path}")
    
    def get_limit_stocks(self):
        """
        获取涨停/跌停股票数据
        
        Returns:
            tuple: (涨停数, 跌停数, 炸板率)
        """
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
                炸板率 = 0
                
                print(f"涨停股票数量: {涨停数}")
                print(f"跌停股票数量: {跌停数}")
                return 涨停数, 跌停数, 炸板率
            else:
                print("数据中缺少'涨跌幅'列，使用默认值")
                return 0, 0, 0
        except Exception as e1:
            print(f"东方财富接口获取失败: {e1}")
            try:
                # 备用方案：使用新浪接口
                spot_df = ak.stock_zh_a_spot()
                print(f"使用新浪接口获取实时股票数据成功，共 {len(spot_df)} 只股票")
                
                if '涨跌幅' in spot_df.columns:
                    limit_up_df = spot_df[spot_df['涨跌幅'] >= 9.9]
                    limit_down_df = spot_df[spot_df['涨跌幅'] <= -9.9]
                    return len(limit_up_df), len(limit_down_df), 0
                else:
                    return 0, 0, 0
            except Exception as e2:
                print(f"所有实时数据接口都失败: {e2}")
                print("使用默认值: 涨停数=0, 跌停数=0, 炸板率=0")
                return 0, 0, 0
