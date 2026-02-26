import pandas as pd
import plotly.express as px
import os
from datetime import datetime, timedelta

def run_analysis():
    current_file = 'nio_swaps.csv'
    history_file = 'nio_swaps_history.csv'
    
    # --- 1. 数据聚合 ---
    data_frames = []
    if os.path.exists(current_file):
        df_now = pd.read_csv(current_file, encoding='utf-8-sig')
        data_frames.append(df_now)
    
    if os.path.exists(history_file):
        df_hist = pd.read_csv(history_file, encoding='utf-8-sig')
        data_frames.append(df_hist)

    if not data_frames: return

    df = pd.concat(data_frames, ignore_index=True)
    
    # 统一列名
    mapping = {'记录时间': '时间', '实时累计换电次数': '次数'}
    for old, new in mapping.items():
        if old in df.columns: df.rename(columns={old: new}, inplace=True)

    def clean_num(v):
        if pd.isna(v): return v
        return str(v).replace(',', '').replace('"', '').strip()

    df['次数'] = pd.to_numeric(df['次数'].apply(clean_num), errors='coerce')
    df['时间'] = pd.to_datetime(df['时间'])
    # 核心：去重并确保时间排序，这对长跨度图表至关重要
    df = df.dropna(subset=['次数', '时间']).drop_duplicates(subset=['时间']).sort_values('时间')

    # --- 2. 预测逻辑 (精准到秒) ---
    latest_record = df.iloc[-1]
    latest_count = int(latest_record['次数'])
    next_milestone = ((latest_count // 10000000) + 1) * 10000000

    # 采用 72h 采样，如果数据不足则使用历史最近两个大点的斜率
    recent_target = latest_record['时间'] - timedelta(days=3)
    df_recent = df[df['时间'] <= recent_target]
    
    if not df_recent.empty:
        start_point = df_recent.iloc[-1]
    else:
        start_point = df.iloc[-2] if len(df) > 1 else df.iloc[0]

    duration_sec = (latest_record['时间'] - start_point['时间']).total_seconds()
    count_gain = latest_count - start_point['次数']
    
    rate_per_sec = count_gain / duration_sec if duration_sec > 0 else 0

    if rate_per_sec > 0:
        rem_swaps = next_milestone - latest_count
        sec_to_go = rem_swaps / rate_per_sec
        finish_dt = latest_record['时间'] + timedelta(seconds=sec_to_go)
        pred_time_str = finish_dt.strftime('%Y-%m-%d %H:%M:%S')
        days_str = f"{sec_to_go / 86400:.2f}"
    else:
        pred_time_str = "计算中..."
        days_str = "--"

    # --- 3. 可视化：全景趋势图 ---
    theme_color = "#00A3E0"
    # 使用包含所有历史点的 df
    fig1 = px.line(df, x='时间', y='次数', template='plotly_dark')
    fig1.update_traces(line=dict(color=theme_color, width=3), fill='tozeroy', fillcolor='rgba(0,163,224,0.05)')
    
    # 针对 8 年跨度的坐标轴优化
    fig1.update_xaxes(rangeslider_visible=True) # 添加时间滑动条，方便缩放看近期细节
    fig1.update_yaxes(autorange=True, tickformat=",d", title="换电总次数")
    fig1.update_layout(
        title="NIO 换电史诗全景 (2018 - 至今)",
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    # --- 4. 生成 HTML ---
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ background: #0b0e14; color: white; font-family: -apple-system, sans-serif; padding: 15px; }}
            .card {{ background: #1a1f28; padding: 20px; border-radius: 15px; border-top: 5px solid {theme_color}; max-width: 950px; margin: auto; }}
            .prediction-card {{ background: linear-gradient(135deg, #1e2530 0%, #2c3e50 100%); padding: 25px; border-radius: 12px; margin: 20px 0; text-align: center; border: 1px solid #3e4b5b; }}
            .highlight {{ color: #f1c40f; font-size: 26px; font-weight: bold; font-family: monospace; letter-spacing: 1px; }}
            .milestone-text {{ font-size: 14px; color: #bdc3c7; margin-bottom: 10px; }}
            .chart-box {{ margin-top: 20px; background: #000; padding: 10px; border-radius: 10px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2 style="margin:0 0 10px 0;">NIO 换电全景监控与预测</h2>
            <div style="font-size: 16px; color: #888;">实时总数：<b style="color:white; font-size:24px;">{latest_count:,}</b></div>

            <div class="prediction-card">
                <div class="milestone-text">🏁 目标里程碑：<b style="color:white;">{next_milestone:,}</b></div>
                <div style="color:#888; font-size:13px; margin-bottom:5px;">预计达成精确时刻</div>
                <div class="highlight">{pred_time_str}</div>
                <div style="margin-top:10px; font-size:15px;">
                    预计还需 <span style="color:#f1c40f; font-weight:bold;">{days_str}</span> 天
                </div>
            </div>

            <div class="chart-box">
                {fig1.to_html(full_html=False, include_plotlyjs='cdn')}
            </div>
            
            <p style="font-size:11px; color:#444; text-align:center; margin-top:15px;">
                历史模式已启用：数据包含 2018 年至今共 {len(df)} 个观测点
            </p>
        </div>
    </body>
    </html>
    """
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == "__main__":
    run_analysis()
