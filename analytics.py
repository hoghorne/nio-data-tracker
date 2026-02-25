import pandas as pd
import plotly.express as px
import os
from datetime import datetime, timedelta

def run_analysis():
    if not os.path.exists('nio_swaps.csv'):
        print("CSV file not found.")
        return

    # 1. 加载并清洗数据
    df = pd.read_csv('nio_swaps.csv', encoding='utf-8-sig')
    df['时间'] = pd.to_datetime(df['时间'])
    df = df.sort_values('时间')

    # 2. 计算统计指标
    latest = df.iloc[-1]
    # 最近24小时平均每小时次数
    day_ago = latest['时间'] - timedelta(hours=24)
    df_24h = df[df['时间'] >= day_ago]
    avg_hour = (df_24h['换电次数'].iloc[-1] - df_24h['换电次数'].iloc[0]) / 24 if len(df_24h) > 1 else 0

    # 3. 生成交互式折线图
    fig = px.line(df, x='时间', y='换电次数', 
                 title='蔚来实时换电次数增长曲线',
                 labels={'换el次数': '累计换电次数', '时间': '采集时间'},
                 template='plotly_white')
    
    # 优化图表外观
    fig.update_traces(line_color='#00A3E0', line_width=2)
    fig.update_layout(hovermode='x unified')

    # 4. 生成 HTML 页面内容
    html_content = f"""
    <html>
    <head>
        <title>NIO 换电数据监控</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: sans-serif; margin: 40px; background: #f4f7f6; }}
            .stats {{ display: flex; gap: 20px; margin-bottom: 20px; }}
            .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; }}
            h2 {{ color: #333; }}
            .value {{ font-size: 24px; font-weight: bold; color: #00A3E0; }}
        </style>
    </head>
    <body>
        <h1>蔚来换电实时看板</h1>
        <div class="stats">
            <div class="card"><div>累计换电次数</div><div class="value">{latest['换电次数']:,}</div></div>
            <div class="card"><div>最近24h平均时速</div><div class="value">{avg_hour:.2f} 次/小时</div></div>
            <div class="card"><div>总站数 (高速)</div><div class="value">{latest['总站数']} ({latest['高速站数']})</div></div>
        </div>
        <div class="card">
            {fig.to_html(full_html=False, include_plotlyjs='cdn')}
        </div>
        <p style="text-align:right; color:gray;">最后更新: {latest['时间']} (UTC+8)</p>
    </body>
    </html>
    """

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("Analysis and HTML report generated.")

if __name__ == "__main__":
    run_analysis()
