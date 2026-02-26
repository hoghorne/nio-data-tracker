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
    
    def load_and_clean(path):
        if not os.path.exists(path):
            return None
        try:
            temp_df = pd.read_csv(path, encoding='utf-8-sig')
            # 清洗列名：去空格、去BOM、转统一名称
            temp_df.columns = temp_df.columns.str.strip().str.replace('\ufeff', '')
            mapping = {'记录时间': '时间', '实时累计换电次数': '次数'}
            temp_df.rename(columns=mapping, inplace=True)
            return temp_df[['时间', '次数']] if '时间' in temp_df.columns and '次数' in temp_df.columns else None
        except Exception as e:
            print(f"Error loading {path}: {e}")
            return None

    # 加载文件
    df_now = load_and_clean(current_file)
    df_hist = load_and_clean(history_file)

    if df_now is not None: data_frames.append(df_now)
    if df_hist is not None: data_frames.append(df_hist)

    if not data_frames:
        print("No valid data found."); return

    # 合并
    df = pd.concat(data_frames, ignore_index=True)

    # --- 2. 向量化数据清洗 (解决 ValueError 的核心) ---
    # 先把“次数”转为字符串，统一处理逗号，再转数字
    df['次数'] = df['次数'].astype(str).str.replace(',', '').str.replace('"', '').str.strip()
    df['次数'] = pd.to_numeric(df['次数'], errors='coerce')
    
    # 时间转换
    df['时间'] = pd.to_datetime(df['时间'], errors='coerce')
    
    # 清理无效记录
    df = df.dropna(subset=['次数', '时间']).drop_duplicates(subset=['时间']).sort_values('时间')

    if df.empty:
        print("Dataframe is empty after cleaning."); return

    # --- 3. 预测逻辑 ---
    latest_record = df.iloc[-1]
    latest_count = int(latest_record['次数'])
    # 自动计算下一个千万里程碑
    next_milestone = ((latest_count // 10000000) + 1) * 10000000

    # 72小时采样逻辑
    target_time = latest_record['时间'] - timedelta(days=3)
    df_recent = df[df['时间'] <= target_time]
    
    # 如果没有3天前的数据，则取最早的一条
    start_point = df_recent.iloc[-1] if not df_recent.empty else df.iloc[0]

    duration_sec = (latest_record['时间'] - start_point['时间']).total_seconds()
    count_gain = latest_count - start_point['次数']
    
    # 计算速率
    if duration_sec > 60: # 至少间隔一分钟
        rate_per_sec = count_gain / duration_sec
        rem_swaps = next_milestone - latest_count
        sec_to_go = rem_swaps / rate_per_sec
        finish_dt = latest_record['时间'] + timedelta(seconds=sec_to_go)
        pred_time_str = finish_dt.strftime('%Y-%m-%d %H:%M:%S')
        days_str = f"{sec_to_go / 86400:.2f}"
    else:
        pred_time_str = "计算中..."
        days_str = "--"

    # --- 4. 可视化 ---
    theme_color = "#00A3E0"
    fig = px.line(df, x='时间', y='次数', template='plotly_dark')
    fig.update_traces(line=dict(color=theme_color, width=3), fill='tozeroy', fillcolor='rgba(0,163,224,0.1)')
    fig.update_xaxes(rangeslider_visible=True, gridcolor='#333')
    fig.update_yaxes(autorange=True, tickformat=",d", gridcolor='#333')
    fig.update_layout(
        title="NIO 换电全景监控与预测 (2018-2026)",
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10,r=10,t=50,b=10)
    )

    # --- 5. HTML 生成 ---
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ background: #0b0e14; color: white; font-family: -apple-system, sans-serif; padding: 15px; }}
            .card {{ background: #1a1f28; padding: 25px; border-radius: 15px; border-top: 5px solid {theme_color}; max-width: 900px; margin: auto; }}
            .predict-box {{ background: linear-gradient(135deg, #1e2530 0%, #2c3e50 100%); padding: 25px; border-radius: 12px; margin: 20px 0; text-align: center; border: 1px solid #3e4b5b; }}
            .highlight {{ color: #f1c40f; font-size: 28px; font-weight: bold; font-family: monospace; }}
            .label {{ color: #888; font-size: 13px; margin-bottom: 5px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2 style="margin:0;">NIO 换电全景大屏</h2>
            <div style="margin: 15px 0;">
                <span class="label">当前实时累计总数</span><br>
                <span style="font-size: 32px; font-weight: bold;">{latest_count:,}</span>
            </div>
            
            <div class="predict-box">
                <div class="label" style="color:#bdc3c7;">🏁 目标里程碑：{next_milestone:,}</div>
                <div style="margin: 10px 0;">预计达成精确时间</div>
                <div class="highlight">{pred_time_str}</div>
                <div style="margin-top: 10px; font-size: 14px; color:#bdc3c7;">
                    距离达成约剩 <b style="color:white;">{days_str}</b> 天
                </div>
            </div>

            <div style="background:#000; padding:10px; border-radius:10px;">
                {fig.to_html(full_html=False, include_plotlyjs='cdn')}
            </div>
            
            <div style="text-align:center; color:#444; font-size:11px; margin-top:15px;">
                已成功整合历史数据 | 最后更新：{latest_record['时间']}
            </div>
        </div>
    </body>
    </html>
    """
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("Success: Analysis completed.")

if __name__ == "__main__":
    run_analysis()
