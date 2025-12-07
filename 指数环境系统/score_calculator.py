import numpy as np


class ScoreCalculator:
    """评分计算类，负责计算各个因子的得分"""
    
    @staticmethod
    def score_funding(north_inflow, vol_ratio):
        """
        资金面评分
        
        Args:
            north_inflow: 北向资金净流入（亿元）
            vol_ratio: 量比
            
        Returns:
            float: 资金面得分（0-5）
        """
        score = 0
        if north_inflow > 50:
            score += 5
        elif north_inflow > 0:
            score += 3
        else:
            score += 1
        
        if vol_ratio > 1.2:
            score += 5
        elif vol_ratio > 0.8:
            score += 3
        else:
            score += 1
        
        return score / 2  # 归一化到0~5
    
    @staticmethod
    def score_sentiment(up, down, bomb):
        """
        情绪面评分
        
        Args:
            up: 涨停数
            down: 跌停数
            bomb: 炸板率
            
        Returns:
            float: 情绪面得分（0-5）
        """
        score = 5
        score += (up - down) / 50
        score -= bomb * 5
        return max(0, min(score, 5))
    
    @staticmethod
    def score_technical(ma5, ma20, ma60, slope5, slope20):
        """
        技术面评分
        
        Args:
            ma5, ma20, ma60: 移动平均线值
            slope5, slope20: 移动平均线斜率
            
        Returns:
            float: 技术面得分（1-5）
        """
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
    
    @staticmethod
    def score_volatility(vol, vol_mean):
        """
        波动率评分
        
        Args:
            vol: 当前波动率
            vol_mean: 平均波动率
            
        Returns:
            float: 波动率得分（2-5）
        """
        if vol < vol_mean:
            return 5
        elif vol < vol_mean * 1.2:
            return 4
        else:
            return 2
    
    def calculate_total_score(self, funding_score, sentiment_score, 
                             technical_score, volatility_score,
                             weights=None):
        """
        计算总分
        
        Args:
            funding_score: 资金面得分
            sentiment_score: 情绪面得分
            technical_score: 技术面得分
            volatility_score: 波动率得分
            weights: 权重字典，默认权重为 {'funding': 0.2, 'sentiment': 0.15, 
                     'technical': 0.25, 'volatility': 0.1}
            
        Returns:
            float: 总分
        """
        if weights is None:
            weights = {
                'funding': 0.2,
                'sentiment': 0.15,
                'technical': 0.25,
                'volatility': 0.1
            }
        
        total = (funding_score * weights['funding'] +
                sentiment_score * weights['sentiment'] +
                technical_score * weights['technical'] +
                volatility_score * weights['volatility'])
        
        return total
