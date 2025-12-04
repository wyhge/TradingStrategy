import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import matplotlib.pyplot as plt

# ======================
# 1️⃣ 模拟数据生成（实际使用时替换为真实因子数据）
# 假设我们有100天的数据，每个样本有 6 个因子，以及第二天沪深300的涨跌标签（1=涨，0=跌）
# 因子举例：北向资金、涨停家数、PE分位、成交量、汇率、政策因子
# ======================

np.random.seed(42)
n_samples = 100

# 模拟因子数据（实际应该用真实数据替换，比如从Excel/CSV/Tushare获取）
data = {
    '北向资金': np.random.uniform(-50, 200, n_samples),      # 模拟北向资金（亿元）
    '涨停家数': np.random.randint(10, 100, n_samples),       # 每日涨停数量
    'PE分位': np.random.uniform(0, 100, n_samples),          # 沪深300 PE分位数
    '成交量': np.random.uniform(0.5, 2.0, n_samples),        # 两市成交量（万亿）
    '汇率': np.random.uniform(6.8, 7.3, n_samples),          # USD/CNY 汇率
    '政策因子': np.random.uniform(0, 10, n_samples),         # 模拟政策支持力度
}

# 模拟标签：第二天沪深300涨跌（1=涨，0=跌）——这里简单根据某些因子生成
# 假如：北向资金多、涨停多、成交量大、政策支持 → 更容易涨
labels = np.where(
    (data['北向资金'] > 100) &
    (data['涨停家数'] > 50) &
    (data['成交量'] > 1.2) &
    (data['政策因子'] > 7),
    1, 0
)

# 构造 DataFrame
df = pd.DataFrame(data)
df['标签'] = labels  # 1 = 涨，0 = 跌

# ======================
# 2️⃣ 数据预处理
# ======================

X = df.drop(columns=['标签'])  # 特征：所有因子
y = df['标签']                 # 标签：涨跌

# 标准化（逻辑回归对尺度敏感，XGBoost可不做，但统一处理更方便）
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 划分训练集和测试集（80%训练，20%测试）
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# ======================
# 3️⃣ 模型1：逻辑回归（Logistic Regression）
# ======================

print("\n=== 逻辑回归模型 ===")

lr = LogisticRegression()
lr.fit(X_train, y_train)

# 预测
y_pred_lr = lr.predict(X_test)
y_prob_lr = lr.predict_proba(X_test)[:, 1]  # 预测为“1（涨）”的概率

# 评估
print("准确率:", accuracy_score(y_test, y_pred_lr))
print(classification_report(y_test, y_pred_lr))

# 查看因子重要性（即每个因子的系数，正代表利好涨，负代表利空）
feature_names = X.columns
lr_coef = pd.DataFrame({
    '因子': feature_names,
    '逻辑回归系数': lr.coef_[0],  # 系数越大，对“涨”贡献越大
}).sort_values(by='逻辑回归系数', ascending=False)

print("\n【逻辑回归因子系数（权重）】—— 正数代表对上涨有正向影响")
print(lr_coef)

# ======================
# 4️⃣ 模型2：XGBoost
# ======================

print("\n=== XGBoost 模型 ===")

xgb_model = xgb.XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)
xgb_model.fit(X_train, y_train)

# 预测
y_pred_xgb = xgb_model.predict(X_test)
y_prob_xgb = xgb_model.predict_proba(X_test)[:, 1]

# 评估
print("准确率:", accuracy_score(y_test, y_pred_xgb))
print(classification_report(y_test, y_pred_xgb))

# 查看特征重要性（XGBoost 自带重要性评估）
xgb_importance = xgb_model.feature_importances_
xgb_feat_imp = pd.DataFrame({
    '因子': feature_names,
    'XGBoost重要性': xgb_importance,
}).sort_values(by='XGBoost重要性', ascending=False)

print("\n【XGBoost因子重要性】—— 数值越大代表该因子越重要")
print(xgb_feat_imp)

# ======================
# 5️⃣ 择时信号生成（融合多个模型）
# ======================

def build_timing_signal(prob_lr, prob_xgb, threshold=0.55):
    """融合多模型概率，输出A股指数择时信号。"""
    ensemble_prob = (prob_lr + prob_xgb) / 2
    signal = np.where(ensemble_prob >= threshold, 1, 0)  # 1=看多，0=观望/看空
    return ensemble_prob, signal

ensemble_prob, timing_signal = build_timing_signal(y_prob_lr, y_prob_xgb, threshold=0.55)

signal_report = pd.DataFrame({
    '样本索引': y_test.index,
    '实际涨跌': y_test.values,
    'LR看多概率': y_prob_lr.round(3),
    'XGB看多概率': y_prob_xgb.round(3),
    '综合看多概率': ensemble_prob.round(3),
    '择时信号(1=看多)': timing_signal,
}).sort_values(by='样本索引').reset_index(drop=True)

print("\n=== A股指数择时信号（融合逻辑回归 + XGBoost）===")
print(signal_report)
print("择时信号准确率:", accuracy_score(y_test, timing_signal).round(3))


# ======================
# 6️⃣ （可选）可视化因子重要性
# ======================

# plt.figure(figsize=(10, 5))
# xgb_feat_imp.set_index('因子')['XGBoost重要性'].plot(kind='bar', color='skyblue')
# plt.title("XGBoost 模型 - 因子重要性排名")
# plt.ylabel("重要性得分")
# plt.xticks(rotation=45)
# plt.tight_layout()
# plt.show()