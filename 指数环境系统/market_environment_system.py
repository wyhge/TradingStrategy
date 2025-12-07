import pandas as pd
import datetime
from data_fetcher import DataFetcher
from score_calculator import ScoreCalculator
from environment_classifier import EnvironmentClassifier


class MarketEnvironmentSystem:
    """市场环境监测系统主类"""
    
    def __init__(self, index_symbol="sh000300", days=60, csv_path="beixiangzijin.csv"):
        """
        初始化系统
        
        Args:
            index_symbol: 指数代码
            days: 分析天数
            csv_path: 北向资金数据CSV文件路径
        """
        self.index_symbol = index_symbol
        self.days = days
        # 在初始化DataFetcher时传入CSV路径
        self.data_fetcher = DataFetcher(csv_path=csv_path)
        self.score_calculator = ScoreCalculator()
        self.classifier = EnvironmentClassifier()
        self.today = datetime.date.today()
        
        # 存储结果
        self.index_data = None
        self.north_inflow_5d = 0
        self.涨停数 = 0
        self.跌停数 = 0
        self.炸板率 = 0
        self.scores = {}
        self.total_score = 0
        self.env_status = ""
    
    def fetch_data(self):
        """获取所有数据"""
        # 获取指数数据
        self.index_data = self.data_fetcher.get_index_data(
            symbol=self.index_symbol, 
            days=self.days
        )
        
        # 获取北向资金数据（只传入days参数，CSV路径已在初始化时设置）
        self.north_inflow_5d = self.data_fetcher.get_northbound_capital(days=5)
        
        # 获取涨停跌停数据
        self.涨停数, self.跌停数, self.炸板率 = self.data_fetcher.get_limit_stocks()
    
    def calculate_scores(self):
        """计算各项得分"""
        latest = self.index_data.iloc[-1]
        
        # 计算各项得分
        self.scores['funding'] = self.score_calculator.score_funding(
            self.north_inflow_5d, 
            latest["量比"]
        )
        
        self.scores['sentiment'] = self.score_calculator.score_sentiment(
            self.涨停数, 
            self.跌停数, 
            self.炸板率
        )
        
        self.scores['technical'] = self.score_calculator.score_technical(
            latest["MA5"], 
            latest["MA20"], 
            latest["MA60"], 
            latest["MA5_slope"], 
            latest["MA20_slope"]
        )
        
        self.scores['volatility'] = self.score_calculator.score_volatility(
            latest["Volatility"],
            self.index_data['Volatility'].mean()
        )
        
        # 计算总分
        self.total_score = self.score_calculator.calculate_total_score(
            self.scores['funding'],
            self.scores['sentiment'],
            self.scores['technical'],
            self.scores['volatility']
        )
    
    def classify_environment(self):
        """分类市场环境"""
        self.env_status = self.classifier.classify(self.total_score)
    
    def run(self):
        """运行完整分析流程"""
        self.fetch_data()
        self.calculate_scores()
        self.classify_environment()
    
    def print_results(self):
        """打印结果"""
        print(f"\n{self.today} 指数环境监测结果：")
        print(f"资金面得分: {self.scores['funding']:.2f}")
        print(f"情绪面得分: {self.scores['sentiment']:.2f}")
        print(f"技术面得分: {self.scores['technical']:.2f}")
        print(f"波动率得分: {self.scores['volatility']:.2f}")
        print(f"总分: {self.total_score:.2f} → 环境判断：{self.env_status}")
    
    def save_results(self, filename="A股指数环境每日监测.csv"):
        """保存结果到CSV"""
        result_df = pd.DataFrame([{
            "日期": self.today,
            "资金面得分": self.scores['funding'],
            "情绪面得分": self.scores['sentiment'],
            "技术面得分": self.scores['technical'],
            "波动率得分": self.scores['volatility'],
            "总分": self.total_score,
            "市场环境": self.env_status
        }])
        result_df.to_csv(filename, index=False, mode="a", 
                        encoding="utf-8-sig", header=not pd.io.common.file_exists(filename))
    
    def get_results_dict(self):
        """获取结果字典"""
        return {
            "日期": self.today,
            "资金面得分": self.scores['funding'],
            "情绪面得分": self.scores['sentiment'],
            "技术面得分": self.scores['technical'],
            "波动率得分": self.scores['volatility'],
            "总分": self.total_score,
            "市场环境": self.env_status
        }
