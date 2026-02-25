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
        print(f"Read CSV Error: {e}"); return

    mapping = {
        '记录时间': '时间', '时间': '时间',
        '实时累计换电次数': '次数',
        '换电站': '总站数', '高速换电站': '高速站数'
    }
    for old_name, new_name in mapping.items():
        if old_name in df.columns:
            df.rename(columns={old_name: new_name}, inplace=True)

    df['时间'] = pd.to_datetime(df['时间'])
    df = df.sort_values('时间')
    df['次数'] = pd.to_numeric(df['次数'], errors='coerce')
    df = df.dropna(subset=['次数'])
    
    # --- 逻辑计算 ---
    latest_record = df.iloc[-1]
    today_date = latest_record['时间'].date()
    df_today = df[df['时间'].dt.date == today_date].copy()
    
    # --- 计算每日换电次数 ---
    daily_swaps_file = 'daily_swaps.csv'
    
    # 获取所有唯一日期
    all_dates = df['时间'].dt.date.unique()
    all_dates = sorted(all_dates)
    
    daily_swaps = []
    
    for i, date in enumerate(all_dates):
        date_start = datetime.combine(date, datetime.min.time())
        date_start = pd.to_datetime(date_start)
        
        # 获取该日最早时间点的换电次数
        df_date = df[df['时间'].dt.date == date]
        if len(df_date) == 0:
            continue
        date_first = df_date.iloc[0]
        date_first_swaps = date_first['次数']
        
        if i < len(all_dates) - 1:
            # 非当日：下一日最早总换电次数 - 该日最早总换电次数
            next_date = all_dates[i + 1]
            next_date_start = datetime.combine(next_date, datetime.min.time())
            next_date_start = pd.to_datetime(next_date_start)
            
            # 查找下一日最早的记录
            df_next = df[df['时间'] >= next_date_start]
            if len(df_next) > 0:
                next_date_first = df_next.iloc[0]
                next_date_first_swaps = next_date_first['次数']
                day_swaps = int(next_date_first_swaps - date_first_swaps)
            else:
                day_swaps = 0
            is_estimated = False
        else:
            # 当日：用最后时间的总换电次数 - 当日0点最早时间的换电次数
            # 计算平均每小时换电次数，再乘以24推算
            if len(df_date) > 1:
                date_last = df_date.iloc[-1]
                time_delta_hours = (date_last['时间'] - date_first['时间']).total_seconds() / 3600
                if time_delta_hours > 0.08:  # 超过5分钟开始计算
                    hourly_rate = (date_last['次数'] - date_first_swaps) / time_delta_hours
                    day_swaps = int(hourly_rate * 24)
                else:
                    day_swaps = 0
            else:
                day_swaps = 0
            is_estimated = True
        
        daily_swaps.append({
            '日期': date.strftime('%Y-%m-%d'),
            '日换电次数': day_swaps,
            '是否推算': '是' if is_estimated else '否'
        })
    
    # 保存每日换电次数到文件
    df_daily = pd.DataFrame(daily_swaps)
    df_daily.to_csv(daily_swaps_file, index=False, encoding='utf-8-sig')
    print(f"Daily swaps data saved to {daily_swaps_file}")
    
    # --- 获取当日换电次数（显示用） ---
    today_swaps = daily_swaps[-1]['日换电次数'] if daily_swaps else 0
    today_estimated = daily_swaps[-1]['是否推算'] if daily_swaps else '否'

    # 最近1小时换电次数：最后一次总换电次数 - 1小时前总换电次数
    one_hour_ago = latest_record['时间'] - timedelta(hours=1)
    # 找到1小时前最接近的记录
    df_1h_before = df[df['时间'] <= one_hour_ago]
    if len(df_1h_before) > 0:
        one_hour_ago_record = df_1h_before.iloc[-1]
        last_hour_swaps = int(latest_record['次数'] - one_hour_ago_record['次数'])
    else:
        last_hour_swaps = 0

    # --- 绘图逻辑 (修正报错点) ---
    theme_color = "#00A3E0"

    # 图 1: 累计换电次数
    fig1 = px.line(df, x='时间', y='次数', template='plotly_dark')
    fig1.update_traces(line=dict(color=theme_color, width=3, shape='spline', smoothing=1.3),
                       fill='tozeroy', fillcolor='rgba(0, 163, 224, 0.1)')
    
    # 【修正处】使用 rangemode="normal" 配合自动缩放，Plotly 会根据数据范围自动锁定 y 轴
    fig1.update_yaxes(
        autorange=True, 
        rangemode="normal", 
        tickformat=",d", 
        gridcolor='#333',
        separatethousands=True
    )
    fig1.update_layout(title="NIO 累计换电趋势", paper_bgcolor='rgba(0,0,0,0)', 
                       plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10,r=10,t=40,b=10))

    # 图 2: 当日换电次数走势（每小时）
    if len(df_today) > 1:
        # 计算每小时累计换电次数
        df_today_sorted = df_today.sort_values('时间')
        df_today_hourly = df_today_sorted.copy()
        
        fig2 = px.line(df_today_hourly, x='时间', y='次数', template='plotly_dark')
        fig2.update_traces(line=dict(color="#2ecc71", width=2))
        fig2.update_yaxes(autorange=True, rangemode="normal", tickformat=",d", gridcolor='#333')
        fig2.update_layout(title="当日换电次数走势", paper_bgcolor='rgba(0,0,0,0)', 
                           plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10,r=10,t=40,b=10))
    else:
        # 数据不足时创建空图表
        fig2 = None

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
                    <div class="label">最近1小时换电次数</div>
                    <div class="value">{last_hour_swaps:,} <small style="font-size:12px">次</small></div>
                </div>
                <div class="stat-box">
                    <div class="label">日换电次数{' (推算)' if today_estimated == '是' else ''}</div>
                    <div class="value">{today_swaps:,} <small style="font-size:12px">次</small></div>
                </div>
            </div>
            <div class="stat-box">
                <div class="label">累计换电总数</div>
                <div class="value" style="font-size: 38px;">{int(latest_record['次数']):,}</div>
            </div>
            <div class="chart-box">{fig1.to_html(full_html=False, include_plotlyjs='cdn')}</div>
            <div class="chart-box">{fig2.to_html(full_html=False, include_plotlyjs='cdn') if fig2 else '<div style="padding:20px; text-align:center; color:#888;">数据不足，无法生成图表</div>'}</div>
        </div>
    </body>
    </html>
    """
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == "__main__":
    run_analysis()
