import pandas as pd
import plotly.express as px
import os
from datetime import datetime, timedelta
import numpy as np

def run_analysis():
    current_file = 'nio_swaps.csv'
    history_file = 'nio_swaps_history.csv'
    
    # --- 1. 数据聚合 ---
    data_frames = []
    
    # 读取实时数据
    if os.path.exists(current_file):
        try:
            df_now = pd.read_csv(current_file, encoding='utf-8-sig')
            # 强制清洗列名，去除空格和隐藏字符
            df_now.columns = df_now.columns.str.strip().str.replace('\ufeff', '')
            data_frames.append(df_now)
        except Exception as e:
            print(f"Read current file error: {e}")
    
    # 读取历史里程碑数据
    if os.path.exists(history_file):
        try:
            df_hist = pd.read_csv(history_file, encoding='utf-8-sig')
            df_hist.columns = df_hist.columns.str.strip().str.replace('\ufeff', '')
            data_frames.append(df_hist)
        except Exception as e:
            print(f"Read history file error: {e}")

    if not data_frames:
        print("No valid data found."); return

    # 合并数据
    df = pd.concat(data_frames, ignore_index=True)
    
    # 统一列名映射
    mapping = {'记录时间': '时间', '实时累计换电次数': '次数'}
    for old, new in mapping.items():
        if old in df.columns:
            df.rename(columns={old: new}, inplace=True)

    # --- 修复逻辑错误：更健壮的数字清洗函数 ---
    def clean_num(v):
        # 如果是空值（None, NaN, NaT）
        if pd.isna(v):
            return np.nan
        # 如果已经是数字类型
        if isinstance(v, (int, float)):
            return float(v)
        # 如果是字符串
        v_str = str(v).replace(',', '').replace('"', '').strip()
        try:
            return float(v_str)
        except:
            return np.nan

    # 执行清洗
    if '次数' in df.columns:
        df['次数'] = df['次数'].apply(clean_num)
    else:
        print(f"Columns found: {df.columns.tolist()}. '次数' not found.")
        return

    df['时间'] = pd.to_datetime(df['时间'], errors='coerce')
    # 彻底清理无效行
    df = df.dropna(subset=['次数', '时间']).drop_duplicates(subset=['时间']).sort_values('时间')

    if df.empty:
        print("Dataframe is empty after cleaning."); return

    # --- 2. 预测逻辑 ---
    latest_record = df.iloc[-1]
    latest_count = int(latest_record['次数'])
    milestone_step = 10000000
    next_milestone = ((latest_count // milestone_step) + 1) * milestone_step

    # 采样逻辑：优先找 72h 前，没有就找 24h 前，再没有就找第一条
    recent_target = latest_record['时间'] - timedelta(days=3)
    df_recent = df[df['时间'] <= recent_target]
    
    if not df_recent.empty:
        start_point = df_recent.iloc[-1]
    else:
        start_point = df.iloc[0]

    duration_sec = (latest_record['时间'] - start_point['时间']).total_seconds()
    count_gain = latest_count - start_point['次数']
    
    rate_per_sec = count_gain / duration_sec if duration_sec > 300 else 0 # 间隔小于5分钟不计增速

    if rate_per_sec > 0:
        rem_swaps = next_milestone - latest_count
        sec_to_go = rem_swaps / rate_per_sec
        finish_dt = latest_record['时间'] + timedelta(seconds=sec_to_go)
        pred_time_str = finish_dt.strftime('%Y-%m-%d %H:%M:%S')
        days_str = f"{sec_to_go / 86400:.2f}"
    else:
        pred_time_str = "计算中..."
        days_str = "--"

    # --- 3. 可视化 ---
    theme_color = "#00A3E0"
    fig1 = px.line(df, x='时间', y='次数', template='plotly_dark')
    fig1.update_traces(line=dict(color=theme_color, width=3), fill='tozeroy', fillcolor='rgba(0,163,224,0.05)')
    fig1.update_xaxes(rangeslider_visible=True)
    fig1.update_yaxes(autorange=True, tickformat=",d", gridcolor='#333')
    fig1.update_layout(
        title="NIO 换电全景趋势 (2018 - 2026)",
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10,r=10,t=50,b=10)
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
            .highlight {{ color: #f1c40f; font-size: 26px; font-weight: bold; font-family: monospace; }}
            .label {{ color: #888; font-size: 13px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>NIO 换电实时监控与预测</h2>
            <div class="label">当前实时累计总数</div>
            <div style="font-size: 36px; font-weight: bold;">{latest_count:,}</div>
            
            <div class="prediction-card">
                <div class="label" style="color:#bdc3c7;">🏁 目标里程碑：{next_milestone:,}</div>
                <div style="margin: 15px 0; font-size: 16px;">预计达成精确时刻</div>
                <div class="highlight">{pred_time_str}</div>
                <div style="margin-top:10px; font-size:14px; color:#bdc3c7;">
                    预计还需 <b>{days_str}</b> 天
                </div>
            </div>

            <div style="background:#000; padding:10px; border-radius:10px;">
                {fig1.to_html(full_html=False, include_plotlyjs='cdn')}
            </div>
            
            <div style="text-align:center; color:#444; font-size:11px; margin-top:15px;">
                已整合历史里程碑与实时采集数据 | 更新于: {latest_record['时间']}
            </div>
        </div>
    </body>
    </html>
    """
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("Analysis successful!")

if __name__ == "__main__":
    run_analysis()
