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
    
    # --- 计算指标 ---
    # 计算实时日频率: (增长量 / 小时差) * 24
    df['diff_time'] = df['时间'].diff().dt.total_seconds() / 3600
    df['diff_count'] = df['次数'].diff()
    df['daily_rate'] = (df['diff_count'] / df['diff_time']) * 24
    
    latest = df.iloc[-1]
    
    # 1h 频率
    one_hour_ago = latest['时间'] - timedelta(hours=1)
    df_1h = df[df['时间'] >= one_hour_ago]
    speed_hour = (df_1h['次数'].iloc[-1] - df_1h['次数'].iloc[0]) / ((df_1h['时间'].iloc[-1] - df_1h['时间'].iloc[0]).total_seconds()/3600) if len(df_1h)>1 else 0
    
    # 实时日频率显示值 (取最后 5 个点的平均值以平滑数值显示)
    speed_day = df['daily_rate'].iloc[-5:].mean() if len(df) > 5 else 0

    # --- 绘图优化 ---
    theme_color = "#00A3E0"
    
    # --- 图 1: 累计次数 (深度优化纵坐标) ---
    fig1 = px.line(df, x='时间', y='次数', template='plotly_dark')
    fig1.update_traces(
        line=dict(color=theme_color, width=4, shape='spline', smoothing=1.3), # 极高平滑度
        fill='tozeroy', 
        fillcolor='rgba(0, 163, 224, 0.1)'
    )
    # 强制不包含 0，并留出 10% 的上下边距让曲线更居中
    fig1.update_yaxes(
        autorange=True, 
        rangemode="nonnegative", # 依然不显示负数
        include_zero=False,      # 彻底禁用从 0 开始
        tickformat=",d",
        gridcolor='#222'
    )
    fig1.update_layout(title="累计换电次数趋势 (实时缩放)", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=40,b=0))

    # 图 2: 实时日频率趋势
    df_rate = df.dropna(subset=['daily_rate']).iloc[1:]
    # 过滤掉一些极端异常值（比如刚启动时的计算偏差）
    upper_bound = df_rate['daily_rate'].quantile(0.95) * 2
    df_rate = df_rate[df_rate['daily_rate'] < upper_bound]

    fig2 = px.line(df_rate, x='时间', y='daily_rate', template='plotly_dark', title="实时换电频率趋势 (次/天)")
    fig2.update_traces(line=dict(color="#2ecc71", width=2, shape='spline'))
    fig2.update_yaxes(autorange=True, tickformat=",d")
    fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=40,b=0))

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
            .chart-container {{ margin-top: 20px; display: grid; grid-template-columns: 1fr; gap: 30px; }}
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
                Last Update: {latest['时间'].strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>
    </body>
    </html>
    """

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("Success: Visual optimized dashboard generated.")

if __name__ == "__main__":
    run_analysis()
