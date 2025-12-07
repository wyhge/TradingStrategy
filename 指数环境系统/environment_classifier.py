


class EnvironmentClassifier:
    """环境分类类，负责根据总分判断市场环境"""
    
    @staticmethod
    def classify(score):
        """
        根据总分分类市场环境
        
        Args:
            score: 总分
            
        Returns:
            str: 市场环境描述
        """
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