import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import date
from 指数环境系统.market_environment_system import MarketEnvironmentSystem

class TestMarketEnvironmentSystem:
    """MarketEnvironmentSystem 单元测试类"""
    
    def setup_method(self):
        """每个测试前的初始化"""
        # 创建测试数据
        self.test_index_data = pd.DataFrame({
            'close': [100, 102, 105, 108, 110] * 12,
            'volume': [1000, 1200, 800, 1500, 1300] * 12,
            'MA5': [100, 101, 103, 105, 107],
            'MA20': [98, 99, 100, 101, 102],
            'MA60': [95, 96, 97, 98, 99],
            'MA5_slope': [0.5, 1.0, 0.8, 1.2, 0.9],
            'MA20_slope': [0.3, 0.4, 0.5, 0.6, 0.7],
            'Volatility': [2.0, 2.1, 2.2, 2.3, 2.4],
            '量比': [1.0, 1.2, 0.8, 1.5, 1.3]
        }, index=range(60))
        
        # Mock 依赖类
        self.mock_data_fetcher = Mock()
        self.mock_score_calculator = Mock()
        self.mock_classifier = Mock()
        
        # 设置 mock 返回值
        self.mock_data_fetcher.get_index_data.return_value = self.test_index_data
        self.mock_data_fetcher.get_northbound_capital.return_value = 250.0  # 250亿元
        self.mock_data_fetcher.get_limit_stocks.return_value = (50, 10, 0.2)  # 涨停50, 跌停10, 炸板率0.2
        
        self.mock_score_calculator.score_funding.return_value = 4.0
        self.mock_score_calculator.score_sentiment.return_value = 3.5
        self.mock_score_calculator.score_technical.return_value = 4.2
        self.mock_score_calculator.score_volatility.return_value = 4.8
        self.mock_score_calculator.calculate_total_score.return_value = 4.1
        
        self.mock_classifier.classify.return_value = "震荡向上"
        
        # 创建测试实例，注入mock依赖
        with patch('指数环境系统.market_environment_system.DataFetcher', return_value=self.mock_data_fetcher), \
             patch('指数环境系统.market_environment_system.ScoreCalculator', return_value=self.mock_score_calculator), \
             patch('指数环境系统.market_environment_system.EnvironmentClassifier', return_value=self.mock_classifier):
            
            self.system = MarketEnvironmentSystem(index_symbol="sh000300", days=60)
    
    def test_initialization(self):
        """测试初始化"""
        assert self.system.index_symbol == "sh000300"
        assert self.system.days == 60
        assert self.system.today == date.today()
        assert self.system.index_data is None
        assert self.system.north_inflow_5d == 0
        assert self.system.涨停数 == 0
        assert self.system.跌停数 == 0
        assert self.system.炸板率 == 0
        assert self.system.scores == {}
        assert self.system.total_score == 0
        assert self.system.env_status == ""
    
    def test_fetch_data_success(self):
        """测试成功获取数据"""
        # 执行数据获取
        self.system.fetch_data()
        
        # 验证方法调用
        self.mock_data_fetcher.get_index_data.assert_called_once_with(
            symbol="sh000300", days=60
        )
        self.mock_data_fetcher.get_northbound_capital.assert_called_once_with("./beixiangzijin.csv", days=5)
        self.mock_data_fetcher.get_limit_stocks.assert_called_once()
        
        # 验证数据赋值
        assert self.system.index_data is not None
        assert self.system.north_inflow_5d == 250.0
        assert self.system.涨停数 == 50
        assert self.system.跌停数 == 10
        assert self.system.炸板率 == 0.2
    
    def test_fetch_data_with_different_parameters(self):
        """测试使用不同参数获取数据"""
        # 创建新实例测试不同参数
        with patch('指数环境系统.market_environment_system.DataFetcher', return_value=self.mock_data_fetcher), \
             patch('指数环境系统.market_environment_system.ScoreCalculator', return_value=self.mock_score_calculator), \
             patch('指数环境系统.market_environment_system.EnvironmentClassifier', return_value=self.mock_classifier):
            
            custom_system = MarketEnvironmentSystem(index_symbol="sz399001", days=30)
            custom_system.fetch_data()
            
            self.mock_data_fetcher.get_index_data.assert_called_with(
                symbol="sz399001", days=30
            )
    
    def test_calculate_scores(self):
        """测试分数计算"""
        # 先获取数据
        self.system.fetch_data()
        
        # 执行分数计算
        self.system.calculate_scores()
        
        # 验证分数计算方法的调用
        latest = self.test_index_data.iloc[-1]
        self.mock_score_calculator.score_funding.assert_called_once_with(250.0, latest["量比"])
        self.mock_score_calculator.score_sentiment.assert_called_once_with(50, 10, 0.2)
        self.mock_score_calculator.score_technical.assert_called_once_with(
            latest["MA5"], latest["MA20"], latest["MA60"], 
            latest["MA5_slope"], latest["MA20_slope"]
        )
        self.mock_score_calculator.score_volatility.assert_called_once_with(
            latest["Volatility"], self.test_index_data['Volatility'].mean()
        )
        self.mock_score_calculator.calculate_total_score.assert_called_once_with(4.0, 3.5, 4.2, 4.8)
        
        # 验证分数赋值
        assert self.system.scores['funding'] == 4.0
        assert self.system.scores['sentiment'] == 3.5
        assert self.system.scores['technical'] == 4.2
        assert self.system.scores['volatility'] == 4.8
        assert self.system.total_score == 4.1
    
    def test_classify_environment(self):
        """测试环境分类"""
        # 先获取数据和计算分数
        self.system.fetch_data()
        self.system.calculate_scores()
        
        # 执行环境分类
        self.system.classify_environment()
        
        # 验证分类器调用
        self.mock_classifier.classify.assert_called_once_with(4.1)
        
        # 验证环境状态赋值
        assert self.system.env_status == "震荡向上"
    
    def test_run_complete_analysis(self):
        """测试完整分析流程"""
        # 执行完整流程
        self.system.run()
        
        # 验证所有步骤都被调用
        self.mock_data_fetcher.get_index_data.assert_called_once()
        self.mock_data_fetcher.get_northbound_capital.assert_called_once()
        self.mock_data_fetcher.get_limit_stocks.assert_called_once()
        
        # 验证分数计算
        assert self.mock_score_calculator.score_funding.call_count == 1
        assert self.mock_score_calculator.score_sentiment.call_count == 1
        assert self.mock_score_calculator.score_technical.call_count == 1
        assert self.mock_score_calculator.score_volatility.call_count == 1
        assert self.mock_score_calculator.calculate_total_score.call_count == 1
        
        # 验证环境分类
        self.mock_classifier.classify.assert_called_once()
        
        # 验证结果状态
        assert self.system.total_score == 4.1
        assert self.system.env_status == "震荡向上"
        assert len(self.system.scores) == 4
    
    def test_get_results_dict(self):
        """测试获取结果字典"""
        # 执行完整流程
        self.system.run()
        
        # 获取结果字典
        result = self.system.get_results_dict()
        
        # 验证结果字典结构
        expected_keys = ["日期", "资金面得分", "情绪面得分", "技术面得分", 
                        "波动率得分", "总分", "市场环境"]
        assert list(result.keys()) == expected_keys
        
        # 验证值
        assert result["日期"] == date.today()
        assert result["资金面得分"] == 4.0
        assert result["情绪面得分"] == 3.5
        assert result["技术面得分"] == 4.2
        assert result["波动率得分"] == 4.8
        assert result["总分"] == 4.1
        assert result["市场环境"] == "震荡向上"
    
    def test_data_fetcher_exception_handling(self):
        """测试数据获取异常处理"""
        # 模拟数据获取异常
        self.mock_data_fetcher.get_index_data.side_effect = Exception("API error")
        self.mock_data_fetcher.get_northbound_capital.side_effect = Exception("CSV error")
        self.mock_data_fetcher.get_limit_stocks.side_effect = Exception("Limit stocks error")
        
        # 执行数据获取
        self.system.fetch_data()
        
        # 验证方法都被调用（即使有异常）
        assert self.mock_data_fetcher.get_index_data.call_count == 1
        assert self.mock_data_fetcher.get_northbound_capital.call_count == 1
        assert self.mock_data_fetcher.get_limit_stocks.call_count == 1
        
        # 验证默认值保持
        assert self.system.north_inflow_5d == 0
        assert self.system.涨停数 == 0
        assert self.system.跌停数 == 0
        assert self.system.炸板率 == 0
    
    def test_edge_case_zero_data(self):
        """测试边界情况：数据全为零"""
        # 设置mock返回零值
        self.mock_data_fetcher.get_northbound_capital.return_value = 0.0
        self.mock_data_fetcher.get_limit_stocks.return_value = (0, 0, 0)
        
        # 执行完整流程
        self.system.run()
        
        # 验证分数计算方法被调用（即使数据为零）
        latest = self.test_index_data.iloc[-1]
        self.mock_score_calculator.score_funding.assert_called_once_with(0.0, latest["量比"])
        self.mock_score_calculator.score_sentiment.assert_called_once_with(0, 0, 0)
    
    def test_edge_case_negative_data(self):
        """测试边界情况：负值数据"""
        # 设置mock返回负值
        self.mock_data_fetcher.get_northbound_capital.return_value = -100.0  # 净流出100亿
        self.mock_data_fetcher.get_limit_stocks.return_value = (10, 50, 0.5)  # 涨停10, 跌停50, 炸板率0.5
        
        # 执行完整流程
        self.system.run()
        
        # 验证分数计算方法被调用
        latest = self.test_index_data.iloc[-1]
        self.mock_score_calculator.score_funding.assert_called_once_with(-100.0, latest["量比"])
        self.mock_score_calculator.score_sentiment.assert_called_once_with(10, 50, 0.5)
    
    @patch('pandas.io.common.file_exists')
    @patch('pandas.DataFrame.to_csv')
    def test_save_results(self, mock_to_csv, mock_file_exists):
        """测试保存结果到CSV"""
        mock_file_exists.return_value = False  # 文件不存在，需要header
        
        # 执行完整流程并保存结果
        self.system.run()
        self.system.save_results("test_output.csv")
        
        # 验证CSV写入
        mock_to_csv.assert_called_once()
        args, kwargs = mock_to_csv.call_args
        assert kwargs['index'] == False
        assert kwargs['mode'] == "a"
        assert kwargs['encoding'] == "utf-8-sig"
        assert kwargs['header'] == True  # 文件不存在，需要header
    
    @patch('pandas.io.common.file_exists')
    @patch('pandas.DataFrame.to_csv')
    def test_save_results_existing_file(self, mock_to_csv, mock_file_exists):
        """测试保存结果到已存在的CSV文件"""
        mock_file_exists.return_value = True  # 文件已存在，不需要header
        
        # 执行完整流程并保存结果
        self.system.run()
        self.system.save_results("test_output.csv")
        
        # 验证CSV写入（无header）
        mock_to_csv.assert_called_once()
        args, kwargs = mock_to_csv.call_args
        assert kwargs['header'] == False  # 文件存在，不需要header
    
    def test_print_results(self, capsys):
        """测试打印结果"""
        # 执行完整流程
        self.system.run()
        
        # 打印结果
        self.system.print_results()
        
        # 捕获输出
        captured = capsys.readouterr()
        output = captured.out
        
        # 验证输出包含关键信息
        assert str(date.today()) in output
        assert "资金面得分" in output
        assert "情绪面得分" in output
        assert "技术面得分" in output
        assert "波动率得分" in output
        assert "总分" in output
        assert "震荡向上" in output

if __name__ == "__main__":
    pytest.main([__file__, "-v"])