import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, timedelta
import numpy as np
import json

def run_analysis():
    current_file = 'nio_swaps.csv'
    history_file = 'nio_swaps_history.csv'
    now_bj = datetime.utcnow() + timedelta(hours=8)
    
    # --- 1. 原始读取与清洗 ---
    def load_raw(path):
        if not os.path.exists(path): return pd.DataFrame()
        try:
            df = pd.read_csv(path, encoding='utf-8-sig')
            df.columns = df.columns.str.strip().str.replace('\ufeff', '')
            mapping = {'记录时间': '时间', '实时累计换电次数': '次数', '换电站': '站数', '总站数': '站数'}
            df.rename(columns=mapping, inplace=True)
            # 只取我们需要的列，防止其他列干扰
            cols = [c for c in ['时间', '次数', '站数'] if c in df.columns]
            return df[cols]
        except: return pd.DataFrame()

    df1 = load_raw(current_file)
    df2 = load_raw(history_file)
    
    # 合并所有原始数据
    df_all = pd.concat([df1, df2], ignore_index=True)
    
    if df_all.empty:
        print("Error: No data loaded"); return

    # --- 2. 核心清洗：强制转换与去重 ---
    # 处理时间：转换为日期格式，删除无法解析的
    df_all['时间'] = pd.to_datetime(df_all['时间'], errors='coerce')
    
    # 处理次数：先转字符串 -> 去掉逗号/空格 -> 转数值 -> 删掉空值
    df_all['次数'] = df_all['次数'].astype(str).str.replace(r'[^\d.]', '', regex=True)
    df_all['次数'] = pd.to_numeric(df_all['次数'], errors='coerce')
    
    # 处理站数
    if '站数' in df_all.columns:
        df_all['站数'] = df_all['站数'].astype(str).str.replace(r'[^\d.]', '', regex=True)
        df_all['站数'] = pd.to_numeric(df_all['站数'], errors='coerce')
    else:
        df_all['站数'] = np.nan

    # 过滤掉异常数据（未来时间或0值）
    df_all = df_all[(df_all['时间'] <= now_bj) & (df_all['次数'] > 0)]
    
    # 彻底去重并按时间排序
    df_all = df_all.dropna(subset=['时间', '次数']).drop_duplicates(subset=['时间']).sort_values('时间')

    if df_all.empty:
        print("Error: Dataframe empty after cleaning"); return

    # --- 3. 计算最新指标 ---
    latest = df_all.iloc[-1]
    latest_count = int(latest['次数'])
    latest_time_str = latest['时间'].strftime('%Y-%m-%d %H:%M:%S')
    
    # 预测逻辑
    next_milestone = ((latest_count // 10000000) + 1) * 10000000
    df_recent = df_all[df_all['时间'] <= (latest['时间'] - timedelta(days=3))]
    start_pt = df_recent.iloc[-1] if not df_recent.empty else df_all.iloc[0]
    
    duration = (latest['时间'] - start_pt['时间']).total_seconds()
    gain = latest_count - start_pt['次数']
    rate = gain / duration if duration > 3600 else 0 # 必须有1小时以上的跨度才计算速率
    
    if rate > 0:
        finish_dt = latest['时间'] + timedelta(seconds=(next_milestone - latest_count) / rate)
        pred_time = finish_dt.strftime('%Y-%m-%d %H:%M:%S')
        days_left = f"{(finish_dt - latest['时间']).total_seconds()/86400:.2f}"
    else:
        pred_time = "采样中..."; days_left = "--"

    # --- 4. 绘图配置 ---
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    theme_color = "#00A3E0"
    
    # 次数线 (左轴)
    fig.add_trace(go.Scatter(
        x=df_all['时间'], y=df_all['次数'], 
        name="换电次数", line=dict(color=theme_color, width=3),
        fill='tozeroy', fillcolor='rgba(0,163,224,0.1)'
    ), secondary_y=False)
    
    # 站数线 (右轴)
    df_stations = df_all.dropna(subset=['站数'])
    if not df_stations.empty:
        fig.add_trace(go.Scatter(
            x=df_stations['时间'], y=df_stations['站_数' if '站_数' in df_stations else '站数'], 
            name="换电站", line=dict(color="#2ecc71", width=2, shape='hv')
        ), secondary_y=True)

    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        hovermode="x unified", margin=dict(l=10,r=10,t=20,b=10), showlegend=False,
        xaxis=dict(gridcolor='#222', rangeslider=dict(visible=True, thickness=0.06)),
        yaxis=dict(gridcolor='#222', tickformat=",d"), 
        yaxis2=dict(showgrid=False, tickformat="d")
    )

    plot_json = fig.to_json()

    # --- 5. HTML 输出 ---
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {{ background: #0b0e14; color: white; font-family: sans-serif; padding: 10px; }}
            .card {{ background: #1a1f28; padding: 20px; border-radius: 15px; max-width: 1000px; margin: auto; border-top: 5px solid {theme_color}; }}
            .predict-box {{ background: linear-gradient(135deg, #1e2530 0%, #2c3e50 100%); padding: 20px; border-radius: 12px; margin: 20px 0; border: 1px solid #333; text-align: center; }}
            .btn-group {{ margin: 15px 0; display: flex; justify-content: center; gap: 5px; flex-wrap: wrap; }}
            button {{ background: #2c3e50; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; }}
            button.active {{ background: {theme_color}; font-weight: bold; }}
            .highlight {{ color: #f1c40f; font-size: 26px; font-weight: bold; font-family: monospace; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2 style="margin:0;">NIO Power INSIGHT</h2>
            <div style="display:flex; justify-content:space-between; margin:20px 0;">
                <div><small style="color:#888;">累计换电次数</small><br><b style="font-size:32px; color:{theme_color};">{latest_count:,}</b></div>
                <div style="text-align:right;"><small style="color:#888;">换电站总数</small><br><b style="font-size:24px; color:#2ecc71;">{int(latest['站数']) if not pd.isna(latest['站数']) else '--'}</b></div>
            </div>
            
            <div class="predict-box">
                <div style="color:#bdc3c7; font-size:14px;">🏁 目标：{next_milestone:,}</div>
                <div style="margin:10px 0;">预计达成：<span class="highlight">{pred_time}</span></div>
                <div>还需约 <b>{days_left}</b> 天</div>
            </div>

            <div class="btn-group">
                <button onclick="zoom(24)">24H</button>
                <button onclick="zoom(24*7)" id="default-btn">7D</button>
                <button onclick="zoom(24*30)">30D</button>
                <button onclick="zoom(24*90)">90D</button>
                <button onclick="zoom(24*365)">1Y</button>
                <button onclick="zoom(0)">ALL</button>
            </div>
            <div id="chart"></div>
        </div>

        <script>
            var plotData = {plot_json};
            var latestTime = new Date("{latest_time_str}").getTime();
            Plotly.newPlot('chart', plotData.data, plotData.layout, {{responsive: true, displayModeBar: false}});

            function zoom(hours) {{
                var update = hours === 0 ? {{ 'xaxis.autorange': true }} : {{
                    'xaxis.range': [new Date(latestTime - hours*3600000).toISOString(), new Date(latestTime).toISOString()],
                    'xaxis.autorange': false
                }};
                Plotly.relayout('chart', update);
                document.querySelectorAll('button').forEach(b => b.classList.remove('active'));
                event.target.classList.add('active');
            }}
            document.getElementById('default-btn').click();
        </script>
    </body>
    </html>
    """
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == "__main__":
    run_analysis()
