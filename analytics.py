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

    if '时间' not in df.columns or '次数' not in df.columns:
        return

    # 数据预处理
    df['时间'] = pd.to_datetime(df['时间'])
    df = df.sort_values('时间')
    df['次数'] = pd.to_numeric(df['次数'], errors='coerce')
    df = df.dropna(subset=['次数'])
    
    latest = df.iloc[-1]
    first = df.iloc[0]

    # --- 逻辑计算 ---
    
    # 1. 计算最近 1 小时速率
    one_hour_ago = latest['时间'] - timedelta(hours=1)
    df_1h = df[df['时间'] >= one_hour_ago]
    if len(df_1h) > 1:
        h_diff = (df_1h['时间'].iloc[-1] - df_1h['时间'].iloc[0]).total_seconds() / 3600
        count_h = df_1h['次数'].iloc[-1] - df_1h['次数'].iloc[0]
        speed_hour = count_h / h_diff if h_diff > 0 else 0
    else:
        speed_hour = 0

    # 2. 计算平均每天换电次数 (日均增长)
    # 取全部记录的时间跨度
    total_days = (latest['时间'] - first['时间']).total_seconds() / 86400
    total_swaps = latest['次数'] - first['次数']
    
    # 如果数据记录不足 1 小时，显示 0；否则按比例换算成日增长
    if total_days > 0.04: # 约 1 小时以上
        speed_day = total_swaps / total_days
    else:
        speed_day = 0

    # 3. 绘图
    theme_color = "#00A3E0" # 蔚来蓝
    fig = px.line(df, x='时间', y='次数', template='plotly_dark')
    fig.update_traces(line_color=theme_color, fill='tozeroy')
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=10, b=10)
    )

    # 4. 构建 HTML (包含你的文字修改需求)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>NIO Battery Swap Tracker</title>
        <style>
            body {{ background: #0b0e14; color: white; font-family: -apple-system, sans-serif; padding: 20px; }}
            .card {{ background: #1a1f28; padding: 25px; border-radius: 15px; border-top: 5px solid {theme_color}; max-width: 900px; margin: auto; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
            .header-title {{ font-size: 28px; font-weight: bold; margin-bottom: 20px; color: white; }}
            .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }}
            .stat-box {{ background: #252b36; padding: 15px; border-radius: 10px; }}
            .label {{ color: #888; font-size: 14px; }}
            .value {{ font-size: 24px; color: {theme_color}; font-weight: bold; margin-top: 5px; }}
            .small-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 20px; border-top: 1px solid #333; padding-top: 20px; }}
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
                    <div class="label">平均换电增长 (每天)</div>
                    <div class="value">{int(speed_day):,} <span style="font-size:12px">次/day</span></div>
                </div>
            </div>

            <div class="stat-box" style="margin-bottom: 20px;">
                <div class="label">全网累计换电总数</div>
                <div class="value" style="font-size: 40px;">{int(latest['次数']):,}</div>
            </div>

            {fig.to_html(full_html=False, include_plotlyjs='cdn')}

            <div class="small-grid">
                <div>
                    <div class="label">换电站总数</div>
                    <div style="font-size:18px">{latest.get('总站数', 'N/A')}</div>
                </div>
                <div>
                    <div class="label">高速换电站</div>
                    <div style="font-size:18px">{latest.get('高速站数', 'N/A')}</div>
                </div>
                <div>
                    <div class="label">更新时间</div>
                    <div style="font-size:12px; color:#666;">{latest['时间'].strftime('%m-%d %H:%M')}</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("Success: Updated dashboard generated.")

if __name__ == "__main__":
    run_analysis()
