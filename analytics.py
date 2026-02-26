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
    
    def load_data(path):
        if not os.path.exists(path): return None
        try:
            temp = pd.read_csv(path, encoding='utf-8-sig')
            temp.columns = temp.columns.str.strip().str.replace('\ufeff', '')
            mapping = {'记录时间': '时间', '实时累计换电次数': '次数', '换电站': '站数', '总站数': '站数'}
            temp.rename(columns=mapping, inplace=True)
            return temp
        except: return None

    df_now = load_data(current_file)
    df_hist = load_data(history_file)
    
    def clean_df(df_target):
        if df_target is None: return pd.DataFrame()
        df_target['次数'] = pd.to_numeric(df_target['次数'].astype(str).str.replace(',', ''), errors='coerce')
        df_target['站数'] = pd.to_numeric(df_target['站数'].astype(str).str.replace(',', ''), errors='coerce') if '站数' in df_target.columns else np.nan
        df_target['时间'] = pd.to_datetime(df_target['时间'], errors='coerce')
        df_target = df_target[df_target['时间'] <= now_bj]
        return df_target.dropna(subset=['时间', '次数']).sort_values('时间')

    df_all = pd.concat([clean_df(df_hist), clean_df(df_now)], ignore_index=True).drop_duplicates(subset=['时间']).sort_values('时间')
    if df_all.empty: return

    latest = df_all.iloc[-1]
    latest_time_str = latest['时间'].strftime('%Y-%m-%d %H:%M:%S')
    
    # 预测逻辑
    next_milestone = ((int(latest['次数']) // 10000000) + 1) * 10000000
    df_recent = df_all[df_all['时间'] <= (latest['时间'] - timedelta(days=3))]
    start_pt = df_recent.iloc[-1] if not df_recent.empty else df_all.iloc[0]
    duration = (latest['时间'] - start_pt['时间']).total_seconds()
    rate = (latest['次数'] - start_pt['次数']) / duration if duration > 60 else 0
    finish_dt = latest['时间'] + timedelta(seconds=(next_milestone - latest['次数']) / rate) if rate > 0 else latest['时间']

    # --- 图表 ---
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    theme_color = "#00A3E0"
    
    fig.add_trace(go.Scatter(x=df_all['时间'], y=df_all['次数'], name="换电次数", 
        line=dict(color=theme_color, width=3), fill='tozeroy', fillcolor='rgba(0,163,224,0.1)'), secondary_y=False)
    
    df_stations = df_all.dropna(subset=['站数'])
    if not df_stations.empty:
        fig.add_trace(go.Scatter(x=df_stations['时间'], y=df_stations['站数'], name="换电站", 
            line=dict(color="#2ecc71", width=2, shape='hv')), secondary_y=True)

    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        hovermode="x unified", margin=dict(l=10,r=10,t=20,b=10), showlegend=False,
        xaxis=dict(gridcolor='#222', rangeslider=dict(visible=True, thickness=0.05)),
        yaxis=dict(gridcolor='#222', tickformat=",d"), yaxis2=dict(showgrid=False)
    )

    plot_json = fig.to_json()

    # --- HTML 生成 ---
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {{ background: #0b0e14; color: white; font-family: sans-serif; padding: 15px; text-align: center; }}
            .card {{ background: #1a1f28; padding: 20px; border-radius: 15px; max-width: 1000px; margin: auto; border-top: 5px solid {theme_color}; }}
            .predict-box {{ background: linear-gradient(135deg, #1e2530 0%, #2c3e50 100%); padding: 20px; border-radius: 12px; margin: 20px 0; border: 1px solid #333; }}
            .btn-group {{ margin: 15px 0; display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; }}
            button {{ background: #2c3e50; color: white; border: none; padding: 6px 15px; border-radius: 4px; cursor: pointer; font-size: 13px; transition: 0.3s; }}
            button:hover {{ background: {theme_color}; }}
            button.active {{ background: {theme_color}; font-weight: bold; }}
            .highlight {{ color: #f1c40f; font-size: 28px; font-weight: bold; font-family: monospace; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2 style="margin:0;">NIO Power INSIGHT</h2>
            <div style="display:flex; justify-content:space-between; margin:20px 0;">
                <div style="text-align:left;"><small style="color:#888;">实时换电总数</small><br><b style="font-size:30px; color:{theme_color};">{int(latest['次数']):,}</b></div>
                <div style="text-align:right;"><small style="color:#888;">换电站总数</small><br><b style="font-size:24px; color:#2ecc71;">{int(latest['站数']) if not pd.isna(latest['站数']) else '--'}</b></div>
            </div>
            
            <div class="predict-box">
                <div style="color:#bdc3c7; font-size:14px;">🏁 目标：{next_milestone:,}</div>
                <div style="margin:10px 0;">预计达成：<span class="highlight">{finish_dt.strftime('%Y-%m-%d %H:%M:%S')}</span></div>
                <div>剩余约 <b>{(finish_dt - latest['时间']).total_seconds()/86400:.2f}</b> 天</div>
            </div>

            <div class="btn-group" id="controls">
                <button onclick="zoom(24)">24H</button>
                <button onclick="zoom(24*7)" class="active">7D</button>
                <button onclick="zoom(24*30)">30D</button>
                <button onclick="zoom(24*90)">90D</button>
                <button onclick="zoom(24*180)">180D</button>
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
                var update = {{}};
                if (hours === 0) {{
                    update = {{ 'xaxis.autorange': true }};
                }} else {{
                    var startTime = latestTime - (hours * 60 * 60 * 1000);
                    update = {{
                        'xaxis.range': [new Date(startTime).toISOString(), new Date(latestTime).toISOString()],
                        'xaxis.autorange': false
                    }};
                }}
                
                Plotly.relayout('chart', update);
                
                // 切换按钮状态
                var btns = document.querySelectorAll('button');
                btns.forEach(b => b.classList.remove('active'));
                event.target.classList.add('active');
            }}

            // 初始化显示最近7天
            window.onload = function() {{ zoom(24*7); }};
        </script>
    </body>
    </html>
    """
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == "__main__":
    run_analysis()
