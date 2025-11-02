import tushare as ts
import pandas as pd
from datetime import datetime
import time

# ====== 配置你的 TuShare Token ====== 
TOKEN = '6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9'  # 替换成自己的 TuShare Token
pro = ts.pro_api(TOKEN)

def get_latest_trade_date():
    """获取最近交易日（今天不开盘则取上一个交易日）"""
    today = datetime.now().strftime('%Y%m%d')
    df_trade = pro.trade_cal(exchange='', start_date='20251031', end_date=today)
    df_open = df_trade[df_trade['is_open'] == 1]
    latest_date = df_open.iloc[-1]['cal_date']
    print(f"[信息] 最近交易日：{latest_date}")
    return latest_date

def get_boards_chg(market_type, trade_date, limit=50):
    """获取指定市场的板块涨跌幅（只取 limit 个，并过滤退市）"""
    boards = pro.index_basic(market=market_type)
    # 过滤掉退市板块，仅保留 limit 个板块
    boards = boards[~boards['name'].str.contains('退市')].head(limit)

    data_list = []
    for _, row in boards.iterrows():
        index_code = row['ts_code']
        index_name = row['name']
        try:
            daily = pro.index_daily(ts_code=index_code, trade_date=trade_date)
            if not daily.empty:
                pct_chg = daily.iloc[0]['pct_chg']
                data_list.append({
                    '板块代码': index_code,
                    '板块名称': index_name,
                    '涨跌幅%': pct_chg
                })
            else:
                print(f"[警告] {index_name}({index_code}) 无行情数据")
        except Exception as e:
            print(f"[警告] {index_name}({index_code}) 获取失败: {e}")
        # 控制调用速度（必要时开启）
        # time.sleep(0.3)

    df_result = pd.DataFrame(data_list)
    if not df_result.empty:
        df_result.sort_values(by='涨跌幅%', ascending=False, inplace=True)
    return df_result

if __name__ == "__main__":
    trade_date = get_latest_trade_date()

    # 只获取前50个概念板块
    concept_df = get_boards_chg('CSI', trade_date, limit=500)

    if concept_df.empty:
        print("[错误] 概念板块数据为空，可能是接口权限或频率受限")

    # 取涨幅前5个概念板块
    top5_concept = concept_df.head(5) if not concept_df.empty else pd.DataFrame()

    # 保存到 Excel
    output_file = f"概念板块涨跌幅_{trade_date}.xlsx"
    with pd.ExcelWriter(output_file) as writer:
        concept_df.to_excel(writer, sheet_name="概念板块Top50", index=False)
        top5_concept.to_excel(writer, sheet_name="涨幅前5概念", index=False)

    print(f"[完成] 概念板块数据已保存到 {output_file}")