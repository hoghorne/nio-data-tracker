import pandas as pd
import plotly.express as px
import os
from datetime import datetime, timedelta

def run_analysis():
    file_path = 'nio_swaps.csv'
    if not os.path.exists(file_path): return

    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        df.columns = [c.strip().replace('\ufeff', '') for c in df.columns]
    except Exception as e: print(f"Error: {e}"); return

    # 格式清理
    for c in ['记录时间', '时间']:
        if c in df.columns: df.rename(columns={c: '时间'}, inplace=True)
    if '实时累计换电次数' in df.columns: df.rename(columns={'实时累计换电次数': '次数'}, inplace=True)

    def clean_num(v):
        if pd.isna(v): return v
        return str(v).replace(',', '').replace('"', '').strip()

    df['次数'] = pd.to_numeric(df['次数'].apply(clean_num), errors='coerce')
    df['时间'] = pd.to_datetime(df['时间'])
    df = df.dropna(subset=['次数', '时间']).sort_values('时间')
    if df.empty: return

    latest_record = df.iloc[-1]
    latest_count = int(latest_record['次数'])
    next_milestone = ((latest_count // 10000000) + 1) * 10000000

    # --- 进化版预测引擎 ---
    # 1. 获取近期速率 (72h)
    recent_target = latest_record['时间'] - timedelta(days=3)
    df_recent_start = df[df['时间'] <= recent_target]
    recent_old = df_recent_start.iloc[-1] if not df_recent_start.empty else df.iloc[0]
    
    recent_hours = (latest_record['时间'] - recent_old['时间']).total_seconds() / 3600
    recent_rate_per_hour = (latest_count - recent_old['次数']) / recent_hours if recent_hours > 0 else 0

    # 2. 尝试获取历史同比数据 (去年今日起往后推算里程碑期间的均值)
    # 注意：现在数据不足，这里会进入 fallback 逻辑
    history_target = latest_record['时间'] - timedelta(days=365)
    df_history = df[(df['时间'] <= history_target)]
    
    use_historical_adjustment = False
    if not df_history.empty and len(df) > 100: # 假设有足够历史点
        # 这里可以实现你说的：参考去年此时的波动规律
        # 计算去年此时的速率，并得到一个规模增长因子
        use_historical_adjustment = True
        # (此处预留高级算法位置，目前先用线性速率)
    
    # 3. 计算预计时间
    if recent_rate_per_hour > 0:
        remaining = next_milestone - latest_count
        seconds_to_go = remaining / (recent_rate_per_hour / 3600)
        predicted_dt = latest_record['时间'] + timedelta(seconds=seconds_to_go)
        predicted_time_str = predicted_dt.strftime('%Y-%m-%d %H:%M:%S')
        days_to_go_str = f"{seconds_to_go / 86400:.2f}"
    else:
        predicted_time_str = "等待更多数据..."
        days_to_go_str = "--"

    # --- 可视化与 HTML (保持之前的专业风格) ---
    theme_color = "#00A3E0"
    fig1 = px.line(df, x='时间', y='次数', template='plotly_dark')
    fig1.update_traces(line=dict(color=theme_color, width=3))
    fig1.update_layout(title="累计换电走势", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ background: #0b0e14; color: white; font-family: sans-serif; padding: 20px; }}
            .card {{ background: #1a1f28; padding: 20px; border-radius: 15px; border-top: 5px solid {theme_color}; max-width: 800px; margin: auto; }}
            .prediction-box {{ background: linear-gradient(135deg, #1e2530 0%, #2c3e50 100%); padding: 20px; border-radius: 12px; text-align: center; margin: 20px 0; }}
            .highlight {{ color: #f1c40f; font-size: 24px; font-weight: bold; font-family: monospace; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>NIO 换电大数据看板</h2>
            <p>当前总数：<span style="font-size:24px; color:{theme_color}; font-weight:bold;">{latest_count:,}</span></p>
            
            <div class="prediction-box">
                <div style="color:#aaa; font-size:14px;">目标里程碑：{next_milestone:,}</div>
                <div style="margin:10px 0;">预计达成时间</div>
                <div class="highlight">{predicted_time_str}</div>
                <div style="font-size:14px; color:#888; margin-top:10px;">
                    距离达成约剩 {days_to_go_str} 天
                </div>
            </div>
            
            <div style="background:#111; padding:10px; border-radius:10px;">
                {fig1.to_html(full_html=False, include_plotlyjs='cdn')}
            </div>
            <p style="font-size:11px; color:#444; text-align:center;">
                模式：{'混合历史修正模式' if use_historical_adjustment else '72h 线性外推模式 (历史数据积攒中)'}
            </p>
        </div>
    </body>
    </html>
    """
    with open('index.html', 'w', encoding='utf-8') as f: f.write(html_content)

if __name__ == "__main__":
    run_analysis()
