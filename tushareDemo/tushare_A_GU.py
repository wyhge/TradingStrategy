import tushare as ts
import pandas as pd
import time
from datetime import datetime

# 配置tushare token（已填入你的token）
TOKEN = '6088dc17822487a32d92cb588f75409b9415195a4d7bfd94fa9141a9'
pro = ts.pro_api(TOKEN)

# 全局配置：控制接口调用频率（避免tushare限流）
BATCH_SIZE = 200  # 每批次请求股票数量
DELAY = 0.8  # 每批次请求后延迟时间（秒）


def get_latest_trade_date(date=None):
    """获取最近一个交易日，非交易日自动回退（优化：支持日期格式兼容）"""
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    # 兼容不同日期格式（如'2025-11-03'转'20251103'）
    date = date.replace('-', '').replace('/', '')
    
    try:
        df_trade = pro.trade_cal(exchange='', start_date='20100101', end_date=date)
        df_open = df_trade[df_trade['is_open'] == 1].sort_values('cal_date')
        if not df_open.empty:
            latest_date = df_open.iloc[-1]['cal_date']
            if latest_date != date:
                print(f"[信息] {date} 非交易日，使用最近一个交易日：{latest_date}")
            return latest_date
        else:
            print("[错误] 未查询到有效交易日，返回当前日期")
            return date
    except Exception as e:
        print(f"[错误] 获取交易日历失败：{e}，返回当前日期")
        return date


def get_daily_data(ts_codes, trade_date):
    """批量获取指定股票的日线数据（优化：分批请求+效率提升+容错）"""
    all_data = []
    total_stocks = len(ts_codes)
    print(f"[信息] 开始获取 {total_stocks} 只股票 {trade_date} 日线数据（分批处理，每批{batch_SIZE}只）")
    
    # 分批处理股票列表（避免单次请求过多触发限流）
    for i in range(0, total_stocks, BATCH_SIZE):
        batch_codes = ts_codes[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        print(f"[进度] 处理第 {batch_num} 批（{i+1}-{min(i+BATCH_SIZE, total_stocks)} 只）")
        
        for code in batch_codes:
            try:
                # 获取单只股票日线数据（tushare daily接口暂不支持批量，需循环）
                daily_df = pro.daily(ts_code=code, trade_date=trade_date)
                if not daily_df.empty:
                    row = daily_df.iloc[0]
                    all_data.append({
                        '股票代码': row['ts_code'],
                        '股票名称': get_stock_name(code),  # 补充股票名称（实用优化）
                        '交易日期': row['trade_date'],
                        '开盘价': round(row['open'], 2),
                        '最高价': round(row['high'], 2),
                        '最低价': round(row['low'], 2),
                        '收盘价': round(row['close'], 2),
                        '昨收价': round(row['pre_close'], 2),
                        '涨跌额': round(row['change'], 2),
                        '涨跌幅(%)': round(row['pct_chg'], 2),  # 列名更直观
                        '成交量(手)': int(row['vol']),
                        '成交额(万元)': round(row['amount'] / 10, 2)  # 转换为万元（更易读）
                    })
            except Exception as e:
                print(f"[警告] 股票 {code} 数据获取失败：{str(e)[:30]}...")
        
        # 批次间延迟（避免触发tushare接口频率限制）
        time.sleep(DELAY)
    
    # 生成固定列结构的DataFrame（确保空数据时也有列名）
    result_df = pd.DataFrame(all_data, columns=[
        '股票代码', '股票名称', '交易日期', '开盘价', '最高价', '最低价', '收盘价',
        '昨收价', '涨跌额', '涨跌幅(%)', '成交量(手)', '成交额(万元)'
    ])
    print(f"[完成] 数据获取结束，共成功获取 {len(result_df)} 只股票数据\n")
    return result_df


def get_stock_name(ts_code):
    """根据股票代码获取股票名称（缓存优化，避免重复查询）"""
    global stock_name_cache
    if ts_code in stock_name_cache:
        return stock_name_cache[ts_code]
    try:
        df = pro.stock_basic(ts_code=ts_code, fields='name')
        name = df.iloc[0]['name'] if not df.empty else '未知'
        stock_name_cache[ts_code] = name
        return name
    except Exception as e:
        print(f"[警告] 获取 {ts_code} 名称失败：{e}")
        return '未知'


if __name__ == "__main__":
    # 初始化股票名称缓存（提升效率）
    stock_name_cache = {}
    
    try:
        # 1. 获取所有A股基本信息（仅提取ts_code，减少内存占用）
        print("[信息] 正在获取所有A股基本信息...")
        df_all_basic = pro.stock_basic(exchange='', list_status='L', fields='ts_code,name')
        stock_name_cache = dict(zip(df_all_basic['ts_code'], df_all_basic['name']))  # 批量缓存名称
        ts_codes = df_all_basic['ts_code'].tolist()
        print(f"[完成] 共获取 {len(ts_codes)} 只A股基本信息\n")
        
        # 2. 确定目标交易日（支持手动指定或自动获取）
        target_date = '20251103'  # 手动指定日期（格式：YYYYMMDD）
        # target_date = None  # 自动获取最近交易日（取消注释即可切换）
        trade_date = get_latest_trade_date(target_date)
        
        # 3. 批量获取日线数据
        df_daily = get_daily_data(ts_codes, trade_date)
        
        # 4. 筛选涨幅>5%的股票（核心功能）
        if not df_daily.empty and '涨跌幅(%)' in df_daily.columns:
            filtered_df = df_daily[df_daily['涨跌幅(%)'] > 5].sort_values('涨跌幅(%)', ascending=False)
            print(f"[核心结果] {trade_date} 涨幅大于5%的股票共 {len(filtered_df)} 只")
            
            # 预览前10只股票（直观展示）
            if len(filtered_df) > 0:
                print("\n[涨幅前10名预览]")
                print(filtered_df[['股票代码', '股票名称', '涨跌幅(%)', '收盘价', '成交额(万元)']].head(10).to_string(index=False))
            
            # 保存结果（同时生成CSV和TXT格式，方便不同场景使用）
            csv_file = f"涨幅大于5%的股票_{trade_date}.csv"
            txt_file = f"涨幅大于5%的股票_{trade_date}.txt"
            filtered_df.to_csv(csv_file, index=False, encoding='utf-8-sig')  # utf-8-sig支持中文
            filtered_df.to_csv(txt_file, sep='\t', index=False, encoding='utf-8-sig')
            
            print(f"\n[保存完成] 结果已保存至：")
            print(f"  - CSV文件：{csv_file}")
            print(f"  - TXT文件：{txt_file}")
        else:
            print(f"[结果] {trade_date} 无符合条件的股票（或未获取到有效数据）")
    
    except Exception as e:
        print(f"[严重错误] 程序执行失败：{e}")