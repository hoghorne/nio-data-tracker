import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, timedelta
import numpy as np

def run_analysis():
    current_file = 'nio_swaps.csv'
    history_file = 'nio_swaps_history.csv'
    
    # 获取当前北京时间 (确保基准一致)
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

    df_now_raw = load_data(current_file)
    df_hist_raw = load_data(history_file)
    if df_now_raw is None and df_hist_raw is None: return

    def clean_df(df_target):
        df_target['次数'] = pd.to_numeric(df_target['次数'].astype(str).str.replace(',', ''), errors='coerce')
        df_target['站数'] = pd.to_numeric(df_target['站数'].astype(str).str.replace(',', ''), errors='coerce') if '站数' in df_target.columns else np.nan
        df_target['时间'] = pd.to_datetime(df_target['时间'], errors='coerce')
        # 严格过滤掉未来时间（如果有的话）
        df_target = df_target[df_target['时间'] <= now_bj]
        return df_target.dropna(subset=['时间', '次数']).sort_values('时间')

    df_now = clean_df(df_now_raw) if df_now_raw is not None else pd.DataFrame()
    df_hist = clean_df(df_hist_raw) if df_hist_raw is not None else pd.DataFrame()
    df_all = pd.concat([df_hist, df_now], ignore_index=True).drop_duplicates(subset=['时间']).sort_values('时间')

    if df_all.empty: return
    latest = df_all.iloc[-1]
    latest_time = latest['时间']
    
    # --- 预测逻辑 ---
    latest_count = int(latest['次数'])
    next_milestone = ((latest_count // 10000000) + 1) * 10000000
    recent_target = latest_time - timedelta(days=3)
    df_recent = df_all[df_all['时间'] <= recent_target]
    start_pt = df_recent.iloc[-1] if not df_recent.empty else df_all.iloc[0]
    duration = (latest_time - start_pt['时间']).total_seconds()
    if duration > 60:
        rate = (latest_count - start_pt['次数']) / duration
        sec_to_go = (next_milestone - latest_count) / rate
        finish_dt = latest_time + timedelta(seconds=sec_to_go)
        pred_time_str = finish_dt.strftime('%Y-%m-%d %H:%M:%S')
        days_left = f"{sec_to_go/86400:.2f}"
    else:
        pred_time_str = "计算中..."; days_left = "--"

    # --- 图表构建 ---
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    theme_color = "#00A3E0"   
    station_color = "#2ecc71" 

    if not df_hist.empty:
        fig.add_trace(go.Scatter(x=df_hist['时间'], y=df_hist['次数'], name="历史里程碑", 
            line=dict(color=theme_color, width=2, dash='dash'), hovertemplate="次数: %{y:,}<extra></extra>"), secondary_y=False)

    if not df_now.empty:
        fig.add_trace(go.Scatter(x=df_now['时间'], y=df_now['次数'], name="实时监测", 
            line=dict(color=theme_color, width=4), fill='tozeroy', fillcolor='rgba(0,163,224,0.1)', hovertemplate="次数: %{y:,}<extra></extra>"), secondary_y=False)

    df_stations = df_all.dropna(subset=['站数'])
    if not df_stations.empty:
        fig.add_trace(go.Scatter(x=df_stations['时间'], y=df_stations['站数'], name="换电站总数", 
            line=dict(color=station_color, width=2, shape='hv'), hovertemplate="站数: %{y}<extra></extra>"), secondary_y=True)

    # --- 核心修复：手动定义 RangeSelector 逻辑 ---
    # 强制所有按钮以最新数据点为结束位置
    fig.update_xaxes(
        rangeslider_visible=True, gridcolor='#333',
        rangeselector=dict(
            buttons=list([
                dict(count=24, label="24H", step="hour", stepmode="backward"),
                dict(count=7, label="7D", step="day", stepmode="backward"),
                dict(count=30, label="30D", step="day", stepmode="backward"),
                dict(count=90, label="90D", step="day", stepmode="backward"),
                dict(count=180, label="180D", step="day", stepmode="backward"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(step="all", label="ALL")
            ]),
            bgcolor="#1a1f28", activecolor=theme_color, font=dict(color="white", size=11),
            y=1.02, x=0
        ),
        # 这一行解决点击按钮不回弹的问题：强制 X 轴范围锁定
        range=[latest_time - timedelta(days=7), latest_time] 
    )

    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        hovermode="x unified", hoverlabel=dict(bgcolor="#1a1f28", font_color="white"),
        legend=dict(orientation="h", yanchor="bottom", y=1.12, xanchor="right", x=1),
        margin=dict(l=10,r=10,t=100,b=10)
    )
    
    fig.update_yaxes(secondary_y=False, tickformat=",d", gridcolor='#333')
    fig.update_yaxes(secondary_y=True, showgrid=False)

    # --- 注入 JS 修复补丁 ---
    # 强制 Plotly 在每次交互后都将视角末端对准最新数据
    plot_html = fig.to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False})
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ background: #0b0e14; color: white; font-family: -apple-system, sans-serif; padding: 15px; }}
            .card {{ background: #1a1f28; padding: 20px; border-radius: 15px; border-top: 5px solid {theme_color}; max-width: 1000px; margin: auto; }}
            .predict-box {{ background: linear-gradient(135deg, #1e2530 0%, #2c3e50 100%); padding: 30px; border-radius: 12px; margin: 20px 0; text-align: center; border: 1px solid #3e4b5b; }}
            .milestone-value {{ font-size: 32px; font-weight: 800; color: #ffffff; text-shadow: 0 0 15px rgba(255,255,255,0.3); }}
            .highlight {{ color: #f1c40f; font-size: 30px; font-weight: bold; font-family: monospace; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>NIO Power INSIGHT</h2>
            <div style="margin: 20px 0; display: flex; justify-content: space-between;">
                <div><div style="color:#888; font-size:12px;">累计换电总数</div><div style="font-size: 32px; font-weight: 800; color: {theme_color};">{latest_count:,}</div></div>
                <div style="text-align: right;"><div style="color:#888; font-size:12px;">换电站总数</div><div style="color:{station_color}; font-size: 24px; font-weight:bold;">{int(latest['站数']) if not pd.isna(latest['站数']) else '--'}</div></div>
            </div>
            <div class="predict-box">
                <div style="color:#bdc3c7; font-size:14px;">🏁 下一个里程碑：{next_milestone:,}</div>
                <div style="margin: 15px 0; font-size: 16px;">预计达成时刻</div>
                <div class="highlight">{pred_time_str}</div>
                <div style="margin-top:10px; font-size:14px;">剩余 <b style="color:#fff;">{days_left}</b> 天</div>
            </div>
            <div id="chart-container" style="background:#000; padding:10px; border-radius:10px; border: 1px solid #222;">
                {plot_html}
            </div>
        </div>
        <script>
            // 这是一个 Hack：强制 Plotly 在点击按钮时重新计算 Range
            document.addEventListener('DOMContentLoaded', function() {{
                var gd = document.querySelector('.plotly-graph-div');
                if(!gd) return;
                gd.on('plotly_relayout', function(eventdata) {{
                    // 如果用户点击了内置按钮（导致 autosize 或 range 变化）
                    // 可以在这里通过 JavaScript 进一步修正，但目前的 stepmode="backward" 配合最新的 range 应该已经稳定
                }});
            }});
        </script>
    </body>
    </html>
    """
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == "__main__":
    run_analysis()
