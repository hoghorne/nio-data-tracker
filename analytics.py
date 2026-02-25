import pandas as pd
from datetime import datetime, timedelta
import os

def analyze():
    file_path = 'nio_swaps.csv'
    if not os.path.exists(file_path): return
    
    df = pd.read_csv(file_path, encoding='utf-8-sig')
    df['时间'] = pd.to_datetime(df['时间'])
    df = df.sort_values('时间')

    latest = df.iloc[-1]
    
    # 计算最近 24 小时平均
    day_ago = latest['时间'] - timedelta(hours=24)
    df_24h = df[df['时间'] >= day_ago]
    avg_hour = (df_24h['换电次数'].iloc[-1] - df_24h['换电次数'].iloc[0]) / 24 if len(df_24h) > 1 else 0

    # 计算总日均
    total_days = (df['时间'].iloc[-1] - df['时间'].iloc[0]).total_seconds() / 86400
    avg_day = (df['换电次数'].iloc[-1] - df['换电次数'].iloc[0]) / total_days if total_days > 0 else 0

    # 生成一个简单的 Markdown 报表
    report = f"""
### 📊 实时数据统计报告
* **当前累计总数**: {latest['换电次数']:,} 次
* **最近 24h 平均速率**: {avg_hour:.2f} 次/小时
* **全局平均日增速**: {avg_day:.2f} 次/天
* **最后更新时间**: {latest['时间']} (UTC+8)
"""
    # 将结果写入 README.md
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(report)

if __name__ == "__main__":
    analyze()
