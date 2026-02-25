import pandas as pd
import plotly.express as px
import os
from datetime import datetime, timedelta

def run_analysis():
    if not os.path.exists('nio_swaps.csv'):
        return

    # 1. 加载数据
    df = pd.read_csv('nio_swaps.csv', encoding='utf-8-sig')
    df['时间'] = pd.to_datetime(df['时间'])
    df = df.sort_values('时间')
    latest = df.iloc[-1]

    # 2. 计算速度 (最近1小时)
    one_hour_ago = latest['时间'] - timedelta(hours=1)
    df_recent = df[df['时间'] >= one_hour_ago]
    
    if len(df_recent) > 1:
        # 计算每分钟的频率，再乘以 60 得到当前小时速率
        time_diff = (df_recent['时间'].iloc[-1] - df_recent['时间'].iloc[0]).total_seconds() / 3600
        count_diff = df_recent['换电次数'].iloc[-1] - df_recent['换电次数'].iloc[0]
        current_speed = count_diff / time_diff if time_diff > 0 else 0
    else:
        current_speed = 0

    # 3. 根据速率决定颜色 (阈值可以根据实际观察调整)
    # 低于 500: 冷色调, 500-1000: 中性, 1000+: 活跃
    if current_speed < 500:
        theme_color = "#00A3E0" # 蔚来蓝
        status_text = "平稳"
    elif current_speed < 1000:
        theme_color = "#f39c12" # 橙色
        status_text = "繁忙"
    else:
        theme_color = "#e74c3c" # 红色
        status_text = "极速"

    # 4. 生成精美图表
    fig = px.line(df, x='时间', y='换电次数', 
                 title='累计换电增长曲线 (数据实时采集)',
                 labels={'换电次数': '累计次数', '时间': '时间'},
                 template='plotly_dark') # 改用深色模式更酷
    fig.update_traces(line_color=theme_color, fill='tozeroy', fillcolor='rgba(0,163,224,0.1)')
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color="white",
        margin=dict(l=20, r=20, t=50, b=20)
    )

    # 5. 构建酷炫 HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NIO Power Live</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.ts"></script>
        <style>
            body {{ background: #0b0e14; color: white; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; }}
            .container {{ max-width: 1000px; margin: auto; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2d3436; padding-bottom: 10px; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
            .card {{ background: #1a1f28; padding: 25px; border-radius: 15px; border-left: 5px solid {theme_color}; box-shadow: 0 4px 15px rgba(0,0,0,0.3); transition: 0.3s; }}
            .card:hover {{ transform: translateY(-5px); }}
            .label {{ color: #b2bec3; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }}
            .value {{ font-size: 32px; font-weight: bold; margin-top: 10px; font-family: 'Courier New', monospace; }}
            .status-tag {{ background: {theme_color}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; vertical-align: middle; }}
            .chart-container {{ background: #1a1f28; padding: 20px; border-radius: 15px; margin-top: 20px; }}
            .footer {{ text-align: center; color: #636e72; font-size: 12px; margin-top: 30px; }}
            @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} 100% {{ opacity: 1; }} }}
            .live-dot {{ height: 10px; width: 10px; background-color: {theme_color}; border-radius: 50%; display: inline-block; animation: pulse 1s infinite; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2><span class="live-dot"></span> NIO POWER 实时监控</h2>
                <div class="status-tag">系统状态: {status_text}</div>
            </div>
            
            <div class="stats-grid">
                <div class="card">
                    <div class="label">累计换电总次数</div>
                    <div class="value">{latest['换电次数']:,}</div>
                </div>
                <div class="card">
                    <div class="label">当前换电速率 (小时)</div>
                    <div class="value">{current_speed:.1f} <span style="font-size:16px">次/h</span></div>
                </div>
                <div class="card">
                    <div class="label">累计换电站 / 高速</div>
                    <div class="value">{latest['总站数']} / {latest['高速站数']}</div>
                </div>
            </div>

            <div class="chart-container">
                {fig.to_html(full_html=False, include_plotlyjs=False)}
            </div>

            <div class="footer">
                数据自动采集于甲骨文云服务器 | 最后更新: {latest['时间']} (UTC+8)
            </div>
        </div>
    </body>
    </html>
    """

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == "__main__":
    run_analysis()
