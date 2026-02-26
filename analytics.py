import pandas as pd
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
    
    def load_and_clean(path):
        if not os.path.exists(path): return pd.DataFrame()
        try:
            # 读取数据，确保处理 BOM 
            df = pd.read_csv(path, encoding='utf-8-sig')
            df.columns = df.columns.str.strip().str.replace('\ufeff', '')
            
            # 列名映射
            mapping = {'记录时间': '时间', '实时累计换电次数': '次数', '换电站': '站数', '总站数': '站数'}
            df.rename(columns=mapping, inplace=True)
            
            if '时间' not in df.columns or '次数' not in df.columns: return pd.DataFrame()

            # --- 核心修复：处理带逗号和引号的数字 ---
            # 1. 强制转为字符串 
            # 2. 正则替换：只保留数字，删除逗号、引号、空格等所有非数字字符
            df['次数'] = df['次数'].astype(str).str.replace(r'[^\d]', '', regex=True)
            # 3. 转换为浮点数再转整数
            df['次数'] = pd.to_numeric(df['次数'], errors='coerce')
            
            if '站数' in df.columns:
                df['站数'] = df['站数'].astype(str).str.replace(r'[^\d]', '', regex=True)
                df['站数'] = pd.to_numeric(df['站数'], errors='coerce')

            df['时间'] = pd.to_datetime(df['时间'], errors='coerce')
            return df.dropna(subset=['时间', '次数'])
        except Exception as e:
            print(f"Error: {e}")
            return pd.DataFrame()

    # 合并数据
    df_all = pd.concat([load_clean(history_file), load_clean(current_file)], ignore_index=True)
    if df_all.empty: return

    # 全局清洗：去重、排序、过滤未来数据
    df_all = df_all[df_all['时间'] <= now_bj]
    df_all = df_all.drop_duplicates(subset=['时间']).sort_values('时间')

    # 获取最新状态
    latest = df_all.iloc[-1]
    latest_count = int(latest['次数'])
    latest_time_str = latest['时间'].strftime('%Y-%m-%d %H:%M:%S')
    
    # 预测逻辑 (里程碑)
    next_milestone = ((latest_count // 10000000) + 1) * 10000000
    # 取最近3天的数据计算斜率
    df_recent = df_all[df_all['时间'] >= (latest['时间'] - timedelta(days=3))]
    if len(df_recent) > 1:
        start_pt = df_recent.iloc[0]
        duration = (latest['时间'] - start_pt['时间']).total_seconds()
        gain = latest_count - start_pt['次数']
        rate = gain / duration if duration > 0 else 0
        finish_dt = latest['时间'] + timedelta(seconds=(next_milestone - latest_count) / rate) if rate > 0 else None
    else:
        finish_dt = None

    pred_time = finish_dt.strftime('%Y-%m-%d %H:%M:%S') if finish_dt else "计算中..."
    days_left = f"{(finish_dt - latest['时间']).total_seconds()/86400:.2f}" if finish_dt else "--"

    # --- 绘图 ---
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    theme_color = "#00A3E0"
    
    # 主曲线：换电次数
    fig.add_trace(go.Scatter(
        x=df_all['时间'], y=df_all['次数'], name="换电次数",
        line=dict(color=theme_color, width=3), fill='tozeroy', fillcolor='rgba(0,163,224,0.1)',
        hovertemplate="%{y:,} 次<extra></extra>"
    ), secondary_y=False)
    
    # 副曲线：换电站
    if '站数' in df_all.columns:
        df_sta = df_all.dropna(subset=['站数'])
        fig.add_trace(go.Scatter(
            x=df_sta['时间'], y=df_sta['站数'], name="换电站",
            line=dict(color="#2ecc71", width=2, shape='hv'),
            hovertemplate="%{y} 座<extra></extra>"
        ), secondary_y=True)

    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        hovermode="x unified", margin=dict(l=10,r=10,t=20,b=10), showlegend=False,
        xaxis=dict(gridcolor='#222', rangeslider=dict(visible=True, thickness=0.06)),
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
            body {{ background: #0b0e14; color: white; font-family: -apple-system, sans-serif; padding: 10px; }}
            .card {{ background: #1a1f28; padding: 25px; border-radius: 20px; max-width: 900px; margin: auto; border-top: 6px solid {theme_color}; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
            .predict-box {{ background: linear-gradient(135deg, #1e2530 0%, #2c3e50 100%); padding: 20px; border-radius: 15px; margin: 20px 0; text-align: center; border: 1px solid #333; }}
            .btn-group {{ margin: 15px 0; display: flex; justify-content: center; gap: 6px; flex-wrap: wrap; }}
            button {{ background: #2c3e50; color: #ccc; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; transition: 0.2s; font-size: 13px; }}
            button:hover {{ background: #3e5871; color: white; }}
            button.active {{ background: {theme_color}; color: white; font-weight: bold; }}
            .highlight {{ color: #f1c40f; font-size: 28px; font-weight: bold; font-family: monospace; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2 style="margin:0; font-weight:800; letter-spacing:1px;">NIO Power <span style="font-weight:200;">INSIGHT</span></h2>
            <div style="display:flex; justify-content:space-between; margin:25px 0;">
                <div><small style="color:#888; text-transform:uppercase;">Total Swaps</small><br><b style="font-size:36px; color:{theme_color};">{latest_count:,}</b></div>
                <div style="text-align:right;"><small style="color:#888; text-transform:uppercase;">Stations</small><br><b style="font-size:28px; color:#2ecc71;">{int(latest['站数']) if '站数' in latest else '--'}</b></div>
            </div>
            
            <div class="predict-box">
                <div style="color:#bdc3c7; font-size:14px; margin-bottom:10px;">🎯 NEXT MILESTONE: {next_milestone:,}</div>
                <div style="color:#888; font-size:12px;">ESTIMATED ARRIVAL</div>
                <div class="highlight">{pred_time}</div>
                <div style="margin-top:10px; color:#ddd;">APPROX. <b>{days_left}</b> DAYS REMAINING</div>
            </div>

            <div class="btn-group">
                <button onclick="zoom(24)">24H</button>
                <button onclick="zoom(24*7)" id="def-btn">7D</button>
                <button onclick="zoom(24*30)">30D</button>
                <button onclick="zoom(24*90)">90D</button>
                <button onclick="zoom(24*365)">1Y</button>
                <button onclick="zoom(0)">ALL</button>
            </div>
            <div id="chart"></div>
        </div>

        <script>
            var plotData = {plot_json};
            var latestT = new Date("{latest_time_str}").getTime();
            Plotly.newPlot('chart', plotData.data, plotData.layout, {{responsive: true, displayModeBar: false}});

            function zoom(h) {{
                var update = h === 0 ? {{ 'xaxis.autorange': true }} : {{
                    'xaxis.range': [new Date(latestT - h*3600000).toISOString(), new Date(latestT).toISOString()],
                    'xaxis.autorange': false
                }};
                Plotly.relayout('chart', update);
                document.querySelectorAll('button').forEach(b => b.classList.remove('active'));
                event.target.classList.add('active');
            }}
            document.getElementById('def-btn').click();
        </script>
    </body>
    </html>
    """
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == "__main__":
    run_analysis()
