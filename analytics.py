import pandas as pd
import plotly.express as px
import os
from datetime import datetime, timedelta

def run_analysis():
    # 1. 加载数据
    file_path = 'nio_swaps.csv'
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    # 使用 utf-8-sig 处理可能存在的 BOM 头
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
    except Exception as e:
        print(f"Read CSV Error: {e}")
        return

    # 【核心修复】清理列名：去除空格、换行符及不可见字符
    df.columns = [c.strip().replace('\ufeff', '') for c in df.columns]
    print(f"Current Columns: {df.columns.tolist()}")

    # 【列名映射】确保代码能找到核心字段
    mapping = {
        '时间': ['时间', '日期', 'Time'],
        '次数': ['换电次数', '次数', 'Count'],
        '总站数': ['总站数', '站数', 'Stations'],
        '高速站数': ['高速站数', '高速站', 'Highway']
    }

    for standard_name, aliases in mapping.items():
        for alias in aliases:
            if alias in df.columns and standard_name not in df.columns:
                df.rename(columns={alias: standard_name}, inplace=True)

    # 检查核心列
    if '时间' not in df.columns or '次数' not in df.columns:
        print("Error: Missing required columns '时间' or '次数'")
        return

    # 2. 数据处理
    df['时间'] = pd.to_datetime(df['时间'])
    df = df.sort_values('时间')
    latest = df.iloc[-1]

    # 计算最近 1 小时速率
    one_hour_ago = latest['时间'] - timedelta(hours=1)
    df_recent = df[df['时间'] >= one_hour_ago]
    
    if len(df_recent) > 1:
        time_diff = (df_recent['时间'].iloc[-1] - df_recent['时间'].iloc[0]).total_seconds() / 3600
        count_diff = int(df_recent['次数'].iloc[-1]) - int(df_recent['次数'].iloc[0])
        current_speed = count_diff / time_diff if time_diff > 0 else 0
    else:
        current_speed = 0

    # 3. 动态视觉风格
    if current_speed < 400:
        theme_color = "#00A3E0"  # 蔚来蓝
        status_text = "运行平稳"
    elif current_speed < 800:
        theme_color = "#f39c12"  # 繁忙橙
        status_text = "补能活跃"
    else:
        theme_color = "#e74c3c"  # 极速红
        status_text = "高峰时段"

    # 4. 生成图表
    fig = px.line(df, x='时间', y='次数', 
                 title='NIO 累计换电次数实时趋势',
                 template='plotly_dark')
    
    fig.update_traces(line_color=theme_color, fill='tozeroy', fillcolor=f'rgba({theme_color[1:3]},{theme_color[3:5]},{theme_color[5:7]},0.1)')
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color="white",
        hovermode="x unified"
    )

    # 5. 构建 HTML 页面
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>NIO Power Live Monitor</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.ts"></script>
        <style>
            body {{ background: #0b0e14; color: white; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 20px; }}
            .container {{ max-width: 1100px; margin: auto; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 1px solid #2d3436; padding-bottom: 15px; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
            .card {{ background: #1a1f28; padding: 25px; border-radius: 12px; border-top: 4px solid {theme_color}; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
            .label {{ color: #888; font-size: 14px; margin-bottom: 8px; }}
            .value {{ font-size: 36px; font-weight: 800; color: {theme_color}; }}
            .unit {{ font-size: 16px; color: #555; margin-left: 5px; }}
            .status-dot {{ height: 12px; width: 12px; background-color: {theme_color}; border-radius: 50%; display: inline-block; margin-right: 8px; animation: blink 1.5s infinite; }}
            @keyframes blink {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.3; }} 100% {{ opacity: 1; }} }}
            .chart-box {{ background: #1a1f28; padding: 20px; border-radius: 12px; margin-top: 30px; }}
            .footer {{ margin-top: 40px; text-align: center; color: #444; font-size: 13px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div style="font-size: 24px; font-weight: bold;">NIO Power <span style="color:{theme_color}">Live</span></div>
                <div><span class="status-dot"></span> {status_text}</div>
            </div>
            
            <div class="stats-grid">
                <div class="card">
                    <div class="label">累计换电次数</div>
                    <div class="value">{int(latest['次数']):,}</div>
                </div>
                <div class="card">
                    <div class="label">实时频率 (1h内)</div>
                    <div class="value">{current_speed:.1f}<span class="unit">次 / 小时</span></div>
                </div>
                <div class="card">
                    <div class="label">补能网络 (总站数 / 高速)</div>
                    <div class="value">{latest.get('总站数', 'N/A')} / {latest.get('高速站数', 'N/A')}</div>
                </div>
            </div>

            <div class="chart-box">
                {fig.to_html(full_html=False, include_plotlyjs=False)}
            </div>

            <div class="footer">
                Data Tracked by Oracle Cloud | Last Sync: {latest['时间'].strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)
            </div>
        </div>
    </body>
    </html>
    """

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("Success: Dashboard generated with dynamic theme.")

if __name__ == "__main__":
    run_analysis()
