import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

def run_analysis():
    file_path = 'nio_swaps.csv'
    if not os.path.exists(file_path):
        print("Error: nio_swaps.csv not found.")
        return

    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        df.columns = [c.strip().replace('\ufeff', '') for c in df.columns]
    except Exception as e:
        print(f"Read CSV Error: {e}")
        return

    # 映射表头
    mapping = {
        '时间': '时间', 
        '实时累计换电次数': '次数',
        '换电站': '总站数',       
        '高速换电站': '高速站数'    
    }
    for old_name, new_name in mapping.items():
        if old_name in df.columns:
            df.rename(columns={old_name: new_name}, inplace=True)

    # 数据预处理
    df['时间'] = pd.to_datetime(df['时间'])
    df = df.sort_values('时间')
    df['次数'] = pd.to_numeric(df['次数'], errors='coerce')
    df = df.dropna(subset=['次数'])
    
    # --- 计算核心指标 ---
    
    # 1. 计算每条记录相对于上一条的“实时日频率” (即：增长量 / 时间差 * 24小时)
    # 这样每一行数据都会有一个当下的“日速率”
    df['diff_time'] = df['时间'].diff().dt.total_seconds() / 3600  # 小时差
    df['diff_count'] = df['次数'].diff()
    df['daily_rate'] = (df['diff_count'] / df['diff_time']) * 24
    
    # 2. 最近 1 小时的实时频率 (每小时)
    latest = df.iloc[-1]
    one_hour_ago = latest['时间'] - timedelta(hours=1)
    df_1h = df[df['时间'] >= one_hour_ago]
    if len(df_1h) > 1:
        h_diff = (df_1h['时间'].iloc[-1] - df_1h['时间'].iloc[0]).total_seconds() / 3600
        count_h = df_1h['次数'].iloc[-1] - df_1h['次数'].iloc[0]
        speed_hour = count_h / h_diff if h_diff > 0 else 0
    else:
        speed_hour = 0

    # 3. 实时换电频率 (每天) - 取最近几个数据点的平滑值，防止抖动太剧烈
    speed_day = df['daily_rate'].iloc[-5:].mean() if len(df) > 5 else 0

    # --- 绘图 ---
    theme_color = "#00A3E0"
    
    # 图 1: 累计次数趋势
    fig1 = px.line(df, x='时间', y='次数', template='plotly_dark', title="累计换电次数")
    fig1.update_traces(line_color=theme_color, fill='tozeroy')
    fig1.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=30,b=0))

    # 图 2: 实时日频率趋势
    # 排除掉掉初始的 NaN 和异常值
    df_plot_rate = df.dropna(subset=['daily_rate']).iloc[1:] 
    fig2 = px.line(df_plot_rate, x='时间', y='daily_rate', template='plotly_dark', title="实时换电频率趋势 (次/天)")
    fig2.update_traces(line_color="#2ecc71") # 绿色线条代表速率
    fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=30,b=0))

    # --- HTML 构建 ---
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>NIO Battery Swap Tracker</title>
        <style>
            body {{ background: #0b0e14; color: white; font-family: sans-serif; padding: 20px; }}
            .card {{ background: #1a1f28; padding: 25px; border-radius: 15px; border-top: 5px solid {theme_color}; max-width: 1000px; margin: auto; }}
            .header-title {{ font-size: 28px; font-weight: bold; margin-bottom: 20px; }}
            .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }}
            .stat-box {{ background: #252b36; padding: 15px; border-radius: 10px; }}
            .label {{ color: #888; font-size: 14px; }}
            .value {{ font-size: 24px; color: {theme_color}; font-weight: bold; margin-top: 5px; }}
            .chart-container {{ margin-top: 20px; display: grid; grid-template-columns: 1fr; gap: 20px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header-title">NIO Battery Swap</div>
            
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="label">实时换电频率 (每小时)</div>
                    <div class="value">{speed_hour:.1f} <span style="font-size:12px">次/h</span></div>
                </div>
                <div class="stat-box">
                    <div class="label">实时换电频率 (每天)</div>
                    <div class="value">{int(speed_day):,} <span style="font-size:12px">次/day</span></div>
                </div>
            </div>

            <div class="stat-box" style="margin-bottom: 20px;">
                <div class="label">全网累计换电总数</div>
                <div class="value" style="font-size: 40px;">{int(latest['次数']):,}</div>
            </div>

            <div class="chart-container">
                <div>{fig1.to_html(full_html=False, include_plotlyjs='cdn')}</div>
                <div>{fig2.to_html(full_html=False, include_plotlyjs='cdn')}</div>
            </div>

            <div style="margin-top:20px; color:#444; font-size:12px; text-align:center;">
                Last Update: {latest['时间'].strftime('%Y-%m-%d %H:%M:%S')} | Data points: {len(df)}
            </div>
        </div>
    </body>
    </html>
    """

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("Success: Updated dashboard with dual charts generated.")

if __name__ == "__main__":
    run_analysis()
