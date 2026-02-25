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
        # 读取数据并清理表头
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        df.columns = [c.strip().replace('\ufeff', '') for c in df.columns]
    except Exception as e:
        print(f"Read CSV Error: {e}"); return

    # 映射表头（适配你的 tracker.py 字段）
    mapping = {
        '记录时间': '时间', '时间': '时间',
        '实时累计换电次数': '次数',
        '换电站': '总站数', '高速换电站': '高速站数'
    }
    for old_name, new_name in mapping.items():
        if old_name in df.columns:
            df.rename(columns={old_name: new_name}, inplace=True)

    # 格式转换
    df['时间'] = pd.to_datetime(df['时间'])
    df = df.sort_values('时间')
    df['次数'] = pd.to_numeric(df['次数'], errors='coerce')
    df = df.dropna(subset=['次数'])
    
    # --- 计算实时日频率 (基于当日首尾差值) ---
    latest_record = df.iloc[-1]
    today_date = latest_record['时间'].date()
    
    # 筛选出今天的所有数据
    df_today = df[df['时间'].dt.date == today_date].copy()
    
    if len(df_today) > 1:
        first_point = df_today.iloc[0]
        last_point = df_today.iloc[-1]
        
        # 计算时间差（小时）
        time_delta_h = (last_point['时间'] - first_point['时间']).total_seconds() / 3600
        # 计算增长量
        count_delta = last_point['次数'] - first_point['次数']
        
        # 推算日频率：(增长量 / 时间差) * 24
        # 如果时间跨度太短（比如小于 5 分钟），速率可能极其不稳定，设为 0 或等待更多数据
        if time_delta_h > 0.08: 
            current_daily_rate = (count_delta / time_delta_h) * 24
        else:
            current_daily_rate = 0
    else:
        current_daily_rate = 0

    # 每小时频率（取最近 1 小时记录）
    one_hour_ago = latest_record['时间'] - timedelta(hours=1)
    df_1h = df[df['时间'] >= one_hour_ago]
    if len(df_1h) > 1:
        speed_hour = (df_1h['次数'].iloc[-1] - df_1h['次数'].iloc[0]) / \
                     ((df_1h['时间'].iloc[-1] - df_1h['时间'].iloc[0]).total_seconds()/3600)
    else:
        speed_hour = 0

    # --- 绘图逻辑 ---
    theme_color = "#00A3E0"

    # 图 1: 累计换电次数 (优化纵坐标)
    fig1 = px.line(df, x='时间', y='次数', template='plotly_dark')
    fig1.update_traces(line=dict(color=theme_color, width=3, shape='spline', smoothing=1.3),
                       fill='tozeroy', fillcolor='rgba(0, 163, 224, 0.1)')
    fig1.update_yaxes(autorange=True, include_zero=False, tickformat=",d", gridcolor='#333')
    fig1.update_layout(title="NIO 累计换电趋势 (实时缩放)", paper_bgcolor='rgba(0,0,0,0)', 
                       plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10,r=10,t=40,b=10))

    # 图 2: 实时换电频率趋势 (当日)
    # 我们绘制当日每一刻计算出的“日速率”变化
    df_today['moving_daily_rate'] = df_today.apply(
        lambda x: ((x['次数'] - first_point['次数']) / 
                   ((x['时间'] - first_point['时间']).total_seconds()/3600) * 24)
        if (x['时间'] - first_point['时间']).total_seconds() > 300 else 0, axis=1
    )
    
    fig2 = px.line(df_today[df_today['moving_daily_rate'] > 0], x='时间', y='moving_daily_rate', template='plotly_dark')
    fig2.update_traces(line=dict(color="#2ecc71", width=2))
    fig2.update_yaxes(autorange=True, include_zero=False, tickformat=",d", gridcolor='#333')
    fig2.update_layout(title="当日实时换电频率走势 (次/天)", paper_bgcolor='rgba(0,0,0,0)', 
                       plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10,r=10,t=40,b=10))

    # --- 生成 HTML ---
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ background: #0b0e14; color: white; font-family: sans-serif; padding: 20px; }}
            .card {{ background: #1a1f28; padding: 25px; border-radius: 15px; border-top: 5px solid {theme_color}; max-width: 1000px; margin: auto; }}
            .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }}
            .stat-box {{ background: #252b36; padding: 15px; border-radius: 10px; }}
            .label {{ color: #888; font-size: 14px; }}
            .value {{ font-size: 26px; color: {theme_color}; font-weight: bold; }}
            .chart-box {{ margin-top: 25px; background: #111; padding: 10px; border-radius: 10px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div style="font-size: 28px; font-weight: bold; margin-bottom: 20px;">NIO Battery Swap</div>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="label">实时频率 (每小时)</div>
                    <div class="value">{speed_hour:.1f} <small style="font-size:12px">次/h</small></div>
                </div>
                <div class="stat-box">
                    <div class="label">实时频率 (当日推算)</div>
                    <div class="value">{int(current_daily_rate):,} <small style="font-size:12px">次/day</small></div>
                </div>
            </div>
            <div class="stat-box">
                <div class="label">累计换电总数</div>
                <div class="value" style="font-size: 38px;">{int(latest_record['次数']):,}</div>
            </div>
            <div class="chart-box">{fig1.to_html(full_html=False, include_plotlyjs='cdn')}</div>
            <div class="chart-box">{fig2.to_html(full_html=False, include_plotlyjs='cdn')}</div>
            <div style="text-align:center; color:#444; font-size:12px; margin-top:20px;">
                当日起始数据点: {first_point['时间'].strftime('%H:%M:%S')} | 采样点数量: {len(df_today)}
            </div>
        </div>
    </body>
    </html>
    """
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == "__main__":
    run_analysis()
