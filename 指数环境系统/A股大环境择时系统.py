import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
import xgboost as xgb


"""
========================================
🚀 A股大环境择时系统（示例版）
========================================
功能说明：
1. 使用多个宏观 + 情绪因子（北向资金、涨停家数、PE分位、成交量、汇率、政策因子等）
2. 建立两个模型：逻辑回归 + XGBoost，用于预测“第二天指数涨跌概率”
3. 将模型概率 + 因子打分融合，给出 A股“大环境等级” + 买卖建议

⚠️ 重要说明：
- 本脚本目前用“模拟数据”演示流程，方便你先跑通逻辑；
- 实盘时，你只需要把 `generate_mock_data()` 换成读取真实数据（Excel/CSV/Tushare等），即可无缝迁移。
"""


# ======================
# 1️⃣ 数据准备（这里先用模拟数据）
# ======================

def generate_mock_data(n_samples: int = 250) -> pd.DataFrame:
    """
    生成模拟因子 + 标签数据。
    真实使用时，请改写为：从本地文件 / Tushare / AkShare 读取你的历史数据。
    """
    np.random.seed(42)

    data = {
        "北向资金": np.random.uniform(-80, 250, n_samples),      # 亿元
        "涨停家数": np.random.randint(5, 120, n_samples),        # 只
        "PE分位": np.random.uniform(0, 100, n_samples),          # %
        "成交量": np.random.uniform(0.5, 2.5, n_samples),        # 万亿
        "汇率": np.random.uniform(6.8, 7.4, n_samples),          # USD/CNY
        "政策因子": np.random.uniform(0, 10, n_samples),         # 政策支持力度 0-10
    }

    # 简单规则生成“第二天涨跌标签”：1=涨，0=跌（只是示例，用于训练模型）
    labels = np.where(
        (data["北向资金"] > 80)
        & (data["涨停家数"] > 40)
        & (data["成交量"] > 1.2)
        & (data["政策因子"] > 6),
        1,
        0,
    )

    df = pd.DataFrame(data)
    df["标签"] = labels
    return df


# ======================
# 2️⃣ 建立大环境“因子打分系统”
# ======================

def calc_environment_score(row: pd.Series) -> float:
    """
    根据单日因子，计算一个“大环境综合得分”（仅示例，可按你自己的逻辑改）。
    分值大致区间：-5 ~ +5，越高代表环境越好。
    """
    score = 0.0

    # 北向资金：大幅流入加分，流出减分
    if row["北向资金"] > 100:
        score += 1.5
    elif row["北向资金"] < 0:
        score -= 1.0

    # 涨停家数：越多越代表情绪好
    if row["涨停家数"] > 60:
        score += 1.0
    elif row["涨停家数"] < 20:
        score -= 0.7

    # PE分位：太贵减分，低估适度加分
    if row["PE分位"] > 80:
        score -= 1.0
    elif row["PE分位"] < 30:
        score += 0.8

    # 成交量：极低代表没量，极高有时可能是情绪极端
    if row["成交量"] > 2.0:
        score += 0.5
    elif row["成交量"] < 0.8:
        score -= 0.5

    # 汇率：人民币贬值（汇率升高）一般对股市略偏空
    if row["汇率"] > 7.2:
        score -= 0.5
    elif row["汇率"] < 6.9:
        score += 0.3

    # 政策因子：高分意味着政策偏暖
    if row["政策因子"] > 7:
        score += 1.2
    elif row["政策因子"] < 3:
        score -= 0.8

    return score


def map_env_level(env_score: float, prob_up: float) -> str:
    """
    将“因子得分 + 上涨概率”映射为大环境等级。
    可根据你自己的风险偏好调整阈值。
    """
    # 简单融合：环境综合评分 + 概率偏离 0.5 的程度
    fused = env_score + (prob_up - 0.5) * 4  # 概率放大权重可调

    if fused >= 3:
        return "极强多头（进攻期）"
    elif fused >= 1.5:
        return "强势多头（持股为主）"
    elif fused >= 0.5:
        return "温和多头（适度参与）"
    elif fused >= -0.5:
        return "中性震荡（谨慎，控制仓位）"
    elif fused >= -2:
        return "偏空环境（防守为主）"
    else:
        return "极弱环境（空仓/底仓观望）"


# ======================
# 3️⃣ 训练模型：逻辑回归 + XGBoost
# ======================

def train_models(df: pd.DataFrame):
    feature_cols = ["北向资金", "涨停家数", "PE分位", "成交量", "汇率", "政策因子"]
    X = df[feature_cols]
    y = df["标签"]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42
    )

    # 逻辑回归
    lr = LogisticRegression(max_iter=1000)
    lr.fit(X_train, y_train)

    # XGBoost
    xgb_model = xgb.XGBClassifier(
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
    )
    xgb_model.fit(X_train, y_train)

    # 基本评估
    y_pred_lr = lr.predict(X_test)
    y_prob_lr = lr.predict_proba(X_test)[:, 1]

    y_pred_xgb = xgb_model.predict(X_test)
    y_prob_xgb = xgb_model.predict_proba(X_test)[:, 1]

    print("\n=== 逻辑回归模型评估 ===")
    print("准确率:", accuracy_score(y_test, y_pred_lr))
    print(classification_report(y_test, y_pred_lr))

    print("\n=== XGBoost 模型评估 ===")
    print("准确率:", accuracy_score(y_test, y_pred_xgb))
    print(classification_report(y_test, y_pred_xgb))

    return {
        "scaler": scaler,
        "lr": lr,
        "xgb": xgb_model,
        "feature_cols": feature_cols,
    }


# ======================
# 4️⃣ 生成“大环境择时信号”
# ======================

def build_timing_signal(
    env_df: pd.DataFrame,
    models: dict,
    prob_threshold: float = 0.55,
) -> pd.DataFrame:
    """
    输入原始因子数据 + 训练好的模型，输出每一日：
    - 模型预测上涨概率（LR / XGB / 融合）
    - 因子环境得分
    - 大环境等级 & 操作建议
    """
    feature_cols = models["feature_cols"]
    scaler = models["scaler"]
    lr = models["lr"]
    xgb_model = models["xgb"]

    X = env_df[feature_cols]
    X_scaled = scaler.transform(X)

    prob_lr = lr.predict_proba(X_scaled)[:, 1]
    prob_xgb = xgb_model.predict_proba(X_scaled)[:, 1]
    prob_ensemble = (prob_lr + prob_xgb) / 2

    # 计算因子环境得分 & 等级
    env_scores = env_df.apply(calc_environment_score, axis=1)
    env_levels = [
        map_env_level(score, p) for score, p in zip(env_scores, prob_ensemble)
    ]

    # 根据概率和环境，给出简单的仓位建议（示例，可自调）
    def decide_position(level: str, p: float) -> str:
        if "极强多头" in level:
            return "建议 仓位 80%-100%"
        if "强势多头" in level:
            return "建议 仓位 60%-80%"
        if "温和多头" in level:
            return "建议 仓位 30%-60%"
        if "中性震荡" in level:
            return "建议 仓位 10%-30%"
        if "偏空环境" in level:
            return "建议 仓位 0%-20%，以防守为主"
        return "建议 空仓或极低仓位，等待右侧信号"

    positions = [decide_position(lv, p) for lv, p in zip(env_levels, prob_ensemble)]

    result = env_df.copy()
    result["LR_上涨概率"] = prob_lr
    result["XGB_上涨概率"] = prob_xgb
    result["综合上涨概率"] = prob_ensemble
    result["因子环境得分"] = env_scores
    result["大环境等级"] = env_levels
    result["仓位建议"] = positions

    # 可选：给出一个简单的“看多/观望”二分类信号（用于回测）
    result["多空信号(1多/0空)"] = (prob_ensemble >= prob_threshold).astype(int)

    return result


def main():
    # 1. 准备数据（这里用模拟数据示例）
    df = generate_mock_data(n_samples=250)

    # 2. 训练模型
    models = train_models(df)

    # 3. 生成大环境择时结果
    timing_df = build_timing_signal(df, models, prob_threshold=0.55)

    print("\n=== A股大环境择时结果（最近 20 条） ===")
    cols_to_show = [
        "北向资金",
        "涨停家数",
        "PE分位",
        "成交量",
        "汇率",
        "政策因子",
        "LR_上涨概率",
        "XGB_上涨概率",
        "综合上涨概率",
        "因子环境得分",
        "大环境等级",
        "仓位建议",
        "多空信号(1多/0空)",
    ]
    print(timing_df[cols_to_show].tail(20))


if __name__ == "__main__":
    main()


