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

    mapping = {
        '记录时间': '时间', '时间': '时间',
        '实时累计换电次数': '次数',
        '换电站': '总站数', '高速换电站': '高速站数'
    }
    for old_name, new_name in mapping.items():
        if old_name in df.columns:
            df.rename(columns={old_name: new_name}, inplace=True)

    # 处理带逗号的数字格式
    def clean_number_string(value):
        if pd.isna(value): return value
        if isinstance(value, str):
            return value.replace(',', '').replace('"', '').replace(' ', '').strip()
        return value

    if '次数' in df.columns:
        df['次数'] = df['次数'].apply(clean_number_string)
        df['次数'] = pd.to_numeric(df['次数'], errors='coerce')
    
    df = df.dropna(subset=['次数', '时间'])
    df['时间'] = pd.to_datetime(df['时间'])
    df = df.sort_values('时间')

    if df.empty:
        print("Error: No valid data.")
        return

    # --- 逻辑计算 ---
    latest_record = df.iloc[-1]
    
    # 计算每日换电数据
    daily_swaps_file = 'daily_swaps.csv'
    all_dates = sorted(df['时间'].dt.date.unique())
    daily_swaps = []
    
    for i, date in enumerate(all_dates):
        df_date = df[df['时间'].dt.date == date]
        if df_date.empty: continue
            
        date_first_swaps = df_date.iloc[0]['次数']
        
        if i < len(all_dates) - 1:
            next_date = all_dates[i + 1]
            df_next = df[df['时间'].dt.date >= next_date]
            if not df_next.empty:
                next_date_first_swaps = df_next.iloc[0]['次数']
                day_swaps = int(next_date_first_swaps - date_first_swaps)
            else:
                day_swaps = 0
            is_estimated = False
        else:
            # 当日推算
            if len(df_date) > 1:
                date_last = df_date.iloc[-1]
                time_delta_hours = (date_last['时间'] - df_date.iloc[0]['时间']).total_seconds() / 3600
                if time_delta_hours > 0.05:
                    hourly_rate = (date_last['次数'] - date_first_swaps) / time_delta_hours
                    day_swaps = int(hourly_rate * 24)
                else: day_swaps = 0
            else: day_swaps = 0
            is_estimated = True
        
        daily_swaps.append({
            '日期': date.strftime('%Y-%m-%d'),
            '日换电次数': day_swaps,
            '是否推算': '是' if is_estimated else '否'
        })
    
    df_daily = pd.DataFrame(daily_swaps)
    df_daily.to_csv(daily_swaps_file, index=False, encoding='utf-8-sig')
    
    today_swaps = daily_swaps[-1]['日换电次数'] if daily_swaps else 0
    today_estimated = daily_swaps[-1]['是否推算'] if daily_swaps else '否'

    # 最近1小时增量
    one_hour_ago = latest_record['时间'] - timedelta(hours=1)
    df_1h_before = df[df['时间'] <= one_hour_ago]
    last_hour_swaps = int(latest_record['次数'] - df_1h_before.iloc[-1]['次数']) if not df_1h_before.empty else 0

    # --- 可视化优化 ---
    theme_color = "#00A3E0"
    
    # 图 1: 累计换电趋势 (Y轴优化)
    fig1 = px.line(df, x='时间', y='次数', template='plotly_dark')
    fig1.update_traces(line=dict(color=theme_color, width=3, shape='spline'),
                       fill='tozeroy', fillcolor='rgba(0, 163, 224, 0.1)')
    
    fig1.update_yaxes(
        autorange=True,          # 自动缩放
        fixedrange=False,
        tickformat=",d", 
        gridcolor='#333',
        # 关键：不强制从 0 开始，让 1 亿左右的波动填满图表
        rangemode="normal" 
    )
    fig1.update_layout(title="NIO 累计换电趋势 (动态聚焦)", paper_bgcolor='rgba(0,0,0,0)', 
                       plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10,r=10,t=40,b=10))

    # 图 2: 最近 15 天日增量统计 (柱状图更直观)
    if len(df_daily) > 0:
        df_recent = df_daily.tail(15)
        fig2 = px.bar(df_recent, x='日期', y='日换电次数', 
                      template='plotly_dark',
                      color='是否推算',
                      color_discrete_map={'是': '#555', '否': '#2ecc71'})
        fig2.update_yaxes(tickformat=",d", gridcolor='#333')
        fig2.update_layout(title="最近 15 天日增量统计", paper_bgcolor='rgba(0,0,0,0)', 
                           plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10,r=10,t=40,b=10),
                           showlegend=False)
    else:
        fig2 = None

    # --- 生成 HTML ---
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ background: #0b0e14; color: white; font-family: -apple-system, sans-serif; padding: 20px; }}
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
            <div style="font-size: 28px; font-weight: bold; margin-bottom: 20px;">NIO Battery Swap Dashboard</div>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="label">最近1小时增量</div>
                    <div class="value">{last_hour_swaps:,} <span style="font-size:14px;">次</span></div>
                </div>
                <div class="stat-box">
                    <div class="label">今日增量预估{' (进行中)' if today_estimated == '是' else ''}</div>
                    <div class="value" style="color:#2ecc71;">{today_swaps:,} <span style="font-size:14px;">次</span></div>
                </div>
            </div>
            <div class="stat-box">
                <div class="label">实时累计换电总数</div>
                <div class="value" style="font-size: 42px;">{int(latest_record['次数']):,}</div>
                <div style="color:#555; font-size:12px; margin-top:5px;">数据更新于: {latest_record['时间'].strftime('%Y-%m-%d %H:%M:%S')}</div>
            </div>
            <div class="chart-box">{fig1.to_html(full_html=False, include_plotlyjs='cdn')}</div>
            <div class="chart-box">{fig2.to_html(full_html=False, include_plotlyjs='cdn') if fig2 is not None else ''}</div>
        </div>
    </body>
    </html>
    """
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == "__main__":
    run_analysis()
