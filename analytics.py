import pandas as pd
from datetime import datetime, timedelta

def analyze_nio_data(file_path='repo/nio_swaps.csv'):
    try:
        # 1. 加载数据
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        df['时间'] = pd.to_datetime(df['时间'])
        df = df.sort_values('时间')

        # 2. 获取最新状态
        latest_count = df['换电次数'].iloc[-1]
        latest_time = df['时间'].iloc[-1]
        
        # 3. 计算最近 24 小时平均 (每小时)
        day_ago = latest_time - timedelta(hours=24)
        df_last_24h = df[df['时间'] >= day_ago]
        if len(df_last_24h) > 1:
            diff_24h = df_last_24h['换电次数'].iloc[-1] - df_last_24h['换电次数'].iloc[0]
            avg_per_hour = diff_24h / 24
        else:
            avg_per_hour = 0

        # 4. 计算全量平均 (每天)
        total_days = (df['时间'].iloc[-1] - df['时间'].iloc[0]).total_seconds() / 86400
        total_diff = df['换电次数'].iloc[-1] - df['换电次数'].iloc[0]
        avg_per_day = total_diff / total_days if total_days > 0 else 0

        # 5. 打印报告
        print(f"--- 蔚来换电数据分析报告 ({latest_time}) ---")
        print(f"当前累计总数: {latest_count:,}")
        print(f"最近 24 小时平均: {avg_per_hour:.2f} 次/小时")
        print(f"当前推算的日均: {avg_per_day:.2f} 次/天")
        print(f"-------------------------------------------")

    except Exception as e:
        print(f"计算失败，可能数据量不足: {e}")

if __name__ == "__main__":
    analyze_nio_data()
