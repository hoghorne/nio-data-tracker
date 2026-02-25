import pandas as pd
import plotly.express as px
import os
from datetime import datetime, timedelta

def run_analysis():
    file_path = 'nio_swaps.csv'
    if not os.path.exists(file_path):
        print("Error: nio_swaps.csv not found.")
        return

    try:
        # 使用 utf-8-sig 处理 BOM，清理不可见字符
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        df.columns = [c.strip().replace('\ufeff', '') for c in df.columns]
        print(f"Detected columns: {df.columns.tolist()}")
    except Exception as e:
        print(f"Read CSV Error: {e}")
        return

    # 【精准匹配】对应你的 tracker.py 表头
    mapping = {
        '记录时间': '时间',
        '实时累计换电次数': '次数',
        '换电站': '总站数',      
        '高速换电站': '高速站数'    
    }
    
    # 统一重命名，方便后续逻辑调用
    for old_name, new_name in mapping.items():
        if old_name in df.columns:
            df.rename(columns={old_name: new_name}, inplace=True)

    if '时间' not in df.columns or '次数' not in df.columns:
        print(f"Columns mapping failed. Current columns: {df.columns.tolist()}")
        return

    # 数据转换
    df['时间'] = pd.to_datetime(df['时间'])
    df = df.sort_values('时间')
    
    # 确保‘次数’是数值型，去掉可能存在的非数字字符
    df['次数'] = pd.to_numeric(df['次数'], errors='coerce')
    df = df.dropna(subset=['次数'])
    
    latest = df.iloc[-1]

    # 计算最近 1 小时速率
    one_hour_ago = latest['时间'] - timedelta(hours=1)
    df_recent = df[df['时间'] >= one_hour_ago]
    
    if len(df_recent) > 1:
        time_diff = (df_recent['时间'].iloc[-1] - df_recent['时间'].iloc[0]).total_seconds() / 3600
        count_diff = df_recent['次数'].iloc[-1] - df_recent['次数'].iloc[0]
        current_speed = count_diff / time_diff if time_diff > 0 else 0
    else:
        current_speed = 0

    # 动态颜色
    theme_color = "#00A3E0" if current_speed < 500 else "#f39c12"

    # 生成图表
    fig = px.line(df, x='时间', y='次数', template='plotly_dark')
    fig.update_traces(line_color=theme_color)
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

    # 构建 HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ background: #0b0e14; color: white; font-family: sans-serif; padding: 20px; }}
            .card {{ background: #1a1f28; padding: 20px; border-radius: 10px; border-top: 4px solid {theme_color}; }}
            .value {{ font-size: 32px; color: {theme_color}; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>NIO Power Live</h2>
            <div>累计换电: <span class="value">{int(latest['次数']):,}</span> 次</div>
            <div>当前频率: <span class="value">{current_speed:.1f}</span> 次/小时</div>
            <div>站点总数: {latest.get('总站数', 'N/A')} (高速: {latest.get('高速站数', 'N/A')})</div>
            <div style="margin-top:20px;">{fig.to_html(full_html=False, include_plotlyjs='cdn')}</div>
            <p style="color: #444;">更新时间: {latest['时间']}</p>
        </div>
    </body>
    </html>
    """

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("Success: index.html generated.")

if __name__ == "__main__":
    run_analysis()
