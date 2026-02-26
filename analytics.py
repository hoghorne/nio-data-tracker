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
        # 读取 CSV，考虑到可能存在的特殊字符
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        # 清洗列名
        df.columns = [c.strip().replace('\ufeff', '') for c in df.columns]
    except Exception as e:
        print(f"Read CSV Error: {e}")
        return

    # 列名映射转换
    mapping = {
        '记录时间': '时间', '时间': '时间',
        '实时累计换电次数': '次数',
        '换电站': '总站数', '高速换电站': '高速站数'
    }
    for old_name, new_name in mapping.items():
        if old_name in df.columns:
            df.rename(columns={old_name: new_name}, inplace=True)

    # --- 核心修复：处理带逗号的数字 (例如 "102,612,547") ---
    def clean_number_string(value):
        if pd.isna(value):
            return value
        if isinstance(value, str):
            # 去掉逗号、引号和空格
            clean_val = value.replace(',', '').replace('"', '').replace(' ', '').strip()
            return clean_val
        return value

    if '次数' in df.columns:
        df['次数'] = df['次数'].apply(clean_number_string)
        df['次数'] = pd.to_numeric(df['次数'], errors='coerce')
    
    # 清理掉无法转换为数字的行，并排序
    df = df.dropna(subset=['次数', '时间'])
    df['时间'] = pd.to_datetime(df['时间'])
    df = df.sort_values('时间')

    if df.empty:
        print("Error: No valid data after processing.")
        return

    # --- 逻辑计算 ---
    latest_record = df.iloc[-1]
    today_date = latest_record['时间'].date()
    df_today = df[df['时间'].dt.date == today_date].copy()
    
    # --- 计算每日换电次数 ---
    daily_swaps_file = 'daily_swaps.csv'
    all_dates = sorted(df['时间'].dt.date.unique())
    daily_swaps = []
    
    for i, date in enumerate(all_dates):
        df_date = df[df['时间'].dt.date == date]
        if df_date.empty:
            continue
            
        date_first_swaps = df_date.iloc[0]['次数']
        
        if i < len(all_dates) - 1:
            # 非当日逻辑：下一日首条 - 本日首条
            next_date = all_dates[i + 1]
            df_next = df[df['时间'].dt.date >= next_date]
            if not df_next.empty:
                next_date_first_swaps = df_next.iloc[0]['次数']
                day_swaps = int(next_date_first_swaps - date_first_swaps)
            else:
                day_swaps = 0
            is_estimated = False
        else:
            # 当日逻辑：推算 24 小时数据
            if len(df_date) > 1:
                date_last = df_date.iloc[-1]
                date_first = df_date.iloc[0]
                time_delta_hours = (date_last['时间'] - date_first['时间']).total_seconds() / 3600
                if time_delta_hours > 0.05: # 超过3分钟数据
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
    
    df_daily = pd.DataFrame(daily_swaps)
    df_daily.to_csv(daily_swaps_file, index=False, encoding='utf-8-sig')
    
    # 获取看板数值
    today_swaps = daily_swaps[-1]['日换电次数'] if daily_swaps else 0
    today_estimated = daily_swaps[-1]['是否推算'] if daily_swaps else '否'

    # 最近1小时换电
    one_hour_ago = latest_record['时间'] - timedelta(hours=1)
    df_1h_before = df[df['时间'] <= one_hour_ago]
    last_hour_swaps = int(latest_record['次数'] - df_1h_before.iloc[-1]['次数']) if not df_1h_before.empty else 0

    # --- 可视化 ---
    theme_color = "#00A3E0"
    
    # 图 1: 累计
    fig1 = px.line(df, x='时间', y='次数', template='plotly_dark')
    fig1.update_traces(line=dict(color=theme_color, width=3, shape='spline'),
                       fill='tozeroy', fillcolor='rgba(0, 163, 224, 0.1)')
    fig1.update_yaxes(autorange=True, tickformat=",d", gridcolor='#333')
    fig1.update_layout(title="NIO 累计换电趋势", paper_bgcolor='rgba(0,0,0,0)', 
                       plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10,r=10,t=40,b=10))

    # 图 2: 当日
    if len(df_today) > 1:
        fig2 = px.line(df_today, x='时间', y='次数', template='plotly_dark')
        fig2.update_traces(line=dict(color="#2ecc71", width=2))
        fig2.update_yaxes(autorange=True, tickformat=",d", gridcolor='#333')
        fig2.update_layout(title="当日换电次数走势", paper_bgcolor='rgba(0,0,0,0)', 
                           plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10,r=10,t=40,b=10))
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
            body {{ background: #0b0e14; color: white; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 20px; }}
            .card {{ background: #1a1f28; padding: 25px; border-radius: 15px; border-top: 5px solid {theme_color}; max-width: 1000px; margin: auto; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
            .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }}
            .stat-box {{ background: #252b36; padding: 15px; border-radius: 10px; }}
            .label {{ color: #888; font-size: 14px; margin-bottom: 5px; }}
            .value {{ font-size: 26px; color: {theme_color}; font-weight: bold; }}
            .chart-box {{ margin-top: 25px; background: #111; padding: 10px; border-radius: 10px; }}
            .footer {{ text-align: center; color: #555; font-size: 12px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div style="font-size: 28px; font-weight: bold; margin-bottom: 20px;">NIO Battery Swap Tracker</div>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="label">最近1小时换电次数</div>
                    <div class="value">{last_hour_swaps:,} <span style="font-size:14px; font-weight:normal;">次</span></div>
                </div>
                <div class="stat-box">
                    <div class="label">今日换电预估{' (推算)' if today_estimated == '是' else ''}</div>
                    <div class="value">{today_swaps:,} <span style="font-size:14px; font-weight:normal;">次</span></div>
                </div>
            </div>
            <div class="stat-box">
                <div class="label">实时累计换电总数</div>
                <div class="value" style="font-size: 42px; letter-spacing: 1px;">{int(latest_record['次数']):,}</div>
                <div class="label" style="margin-top:5px;">更新时间: {latest_record['时间'].strftime('%Y-%m-%d %H:%M:%S')}</div>
            </div>
            <div class="chart-box">{fig1.to_html(full_html=False, include_plotlyjs='cdn')}</div>
            <div class="chart-box">{fig2.to_html(full_html=False, include_plotlyjs='cdn') if fig2 else '<div style="padding:40px; text-align:center; color:#555;">今日数据点不足，无法生成走势图</div>'}</div>
        </div>
        <div class="footer">Data synced from Ubuntu Server to GitHub Pages</div>
    </body>
    </html>
    """
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Analysis complete. Dashboard updated to {int(latest_record['次数']):,}")

if __name__ == "__main__":
    run_analysis()
