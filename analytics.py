import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, timedelta
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

def run_analysis():
    current_file = 'nio_swaps.csv'
    
    def load_data(path):
        if not os.path.exists(path): return None
        try:
            temp = pd.read_csv(path, encoding='utf-8-sig')
            temp.columns = temp.columns.str.strip().str.replace('\ufeff', '')
            mapping = {
                '记录时间': '时间', '实时累计换电次数': '次数',
                '换电站': '站数', '总站数': '站数',
                '高速换电站': '高速站'  # 新增：映射高速换电站字段
            }
            temp.rename(columns=mapping, inplace=True)
            for col in ['时间', '次数']:
                if col not in temp.columns: return None
            return temp
        except: return None

    df_now_raw = load_data(current_file)

    if df_now_raw is None: return

    def clean_df(df_target):
        df_target['次数'] = pd.to_numeric(df_target['次数'].astype(str).str.replace(',', ''), errors='coerce')
        
        # 处理总站数
        col_name = '站数' if '站数' in df_target.columns else None
        if col_name:
            df_target['站数'] = pd.to_numeric(df_target[col_name].astype(str).str.replace(',', ''), errors='coerce')
        else:
            df_target['站数'] = np.nan
            
        # 新增：处理高速站数
        h_col_name = '高速站' if '高速站' in df_target.columns else None
        if h_col_name:
            df_target['高速站'] = pd.to_numeric(df_target[h_col_name].astype(str).str.replace(',', ''), errors='coerce')
        else:
            df_target['高速站'] = np.nan

        df_target['时间'] = pd.to_datetime(df_target['时间'], errors='coerce')
        return df_target.dropna(subset=['时间', '次数']).sort_values('时间')

    df_now = clean_df(df_now_raw) if df_now_raw is not None else pd.DataFrame()
    df_all = df_now

    # --- 核心预测逻辑增强 ---
    latest = df_all.iloc[-1]
    latest_count = int(latest['次数'])
    next_milestone = ((latest_count // 10000000) + 1) * 10000000
    prev_milestone = ((latest_count - 1) // 10000000) * 10000000 if latest_count > 0 else 0
    prev_prev_milestone = prev_milestone - 10000000 if prev_milestone > 0 else 0
    
    # 模型 A: 近期线性模型
    recent_target = latest['时间'] - timedelta(days=3)
    df_recent = df_all[df_all['时间'] >= recent_target]
    start_pt = df_recent.iloc[0] if not df_recent.empty else df_all.iloc[0]
    duration = (latest['时间'] - start_pt['时间']).total_seconds()

    if duration > 60:
        rate = (latest['次数'] - start_pt['次数']) / duration
        sec_to_go = (next_milestone - latest['次数']) / rate
        finish_dt = latest['时间'] + timedelta(seconds=sec_to_go)
        pred_time_str = finish_dt.strftime('%Y-%m-%d %H:%M:%S')
        days_left_linear = f"{sec_to_go/86400:.2f}"
    else:
        pred_time_str = "计算中..."; days_left_linear = "--"

    # 模型 B: 历史趋势多项式回归（简化为使用 df_all）
    trend_pred_str = "计算中..."
    days_left_trend = "--"
    df_m = df_all[df_all['次数'] >= 10000000].copy()
    if len(df_m) >= 3:
        m_start = df_m['时间'].min()
        df_m['days'] = (df_m['时间'] - m_start).dt.total_seconds() / 86400
        X = df_m[['days']].values
        y = df_m['次数'].values
        poly = PolynomialFeatures(degree=2)
        model = LinearRegression().fit(poly.fit_transform(X), y)
        
        for d in np.arange(df_m['days'].max(), df_m['days'].max() + 365, 0.01):
            if model.predict(poly.transform([[d]]))[0] >= next_milestone:
                trend_dt = m_start + timedelta(days=float(d))
                trend_pred_str = trend_dt.strftime('%Y-%m-%d %H:%M:%S')
                sec_to_go_trend = (trend_dt - latest['时间']).total_seconds()
                days_left_trend = f"{max(0, sec_to_go_trend/86400):.2f}"
                break

    # --- 可视化配置 ---
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 移除 df_hist 相关的可视化代码（已整合到 df_now）
    theme_color = "#00A3E0"   
    station_color = "#FF8C00"

    # 处理实时监测数据 - 按间隔分割为多个trace
    if not df_now.empty:
        dates = df_now['时间'].tolist()
        counts = df_now['次数'].tolist()
        
        # 分割数据点
        segments = []
        current_segment = {'x': [], 'y': []}
        
        for i, (date, count) in enumerate(zip(dates, counts)):
            if i == 0:
                current_segment['x'].append(date)
                current_segment['y'].append(count)
            else:
                gap_days = (date - dates[i-1]).total_seconds() / 86400
                if gap_days > 7:
                    # 保存当前段
                    if len(current_segment['x']) > 0:
                        segments.append(current_segment.copy())
                    # 开始新段
                    current_segment = {'x': [date], 'y': [count]}
                else:
                    current_segment['x'].append(date)
                    current_segment['y'].append(count)
        
        # 保存最后一段
        if len(current_segment['x']) > 0:
            segments.append(current_segment)
        
        # 为每个段创建trace
        for idx, seg in enumerate(segments):
            if idx == 0:
                name = "实时监测数据"
                showlegend = True
            else:
                name = None
                showlegend = False
            
            fig.add_trace(go.Scatter(
                x=seg['x'], y=seg['y'],
                name=name, showlegend=showlegend,
                line=dict(color=theme_color, width=4),
                hovertemplate="<b>实时监测</b><br>时间: %{x}<br>次数: %{y:,}<extra></extra>"
            ), secondary_y=False)
        
        # 创建虚线段用于显示间隔
        for i in range(1, len(dates)):
            gap_days = (dates[i] - dates[i-1]).total_seconds() / 86400
            if gap_days > 7:
                fig.add_trace(go.Scatter(
                    x=[dates[i-1], dates[i]],
                    y=[counts[i-1], counts[i]],
                    name=None, showlegend=False,
                    line=dict(color=theme_color, width=4, dash='dash'),
                    hovertemplate="<b>数据间隔</b><br>间隔: {gap_days:.1f}天<extra></extra>".format(gap_days=gap_days)
                ), secondary_y=False)

    # 历史数据已整合到 df_now 中，df_stations 从 df_all 中提取
    df_stations = df_all.dropna(subset=['站数'])
    if not df_stations.empty:
        fig.add_trace(go.Scatter(
            x=df_stations['时间'], y=df_stations['站数'],
            name="换电站总数", line=dict(color=station_color, width=2, shape='hv'),
            hovertemplate="<b>换电站分布</b><br>时间: %{x}<br>站数: %{y}<extra></extra>"
        ), secondary_y=True)

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#1a1f28", font_size=14, font_family="monospace", font_color="white"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10,r=10,t=40,b=10)
    )
    
    fig.update_xaxes(rangeslider_visible=True, gridcolor='#333')
    fig.update_yaxes(title_text="换电总次数", secondary_y=False, tickformat=",d", gridcolor='#333', rangemode='normal')
    fig.update_yaxes(title_text="换电站数量", secondary_y=True, showgrid=False)

    # 获取最新的高速站数据
    latest_highway_stations = int(latest['高速站']) if '高速站' in latest and not pd.isna(latest['高速站']) else '--'

    # --- HTML 渲染 ---
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>NIO Power Insight</title>
        <style>
            body {{ background: #0b0e14; color: white; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; padding: 15px; }}
            .card {{ background: #1a1f28; padding: 20px; border-radius: 15px; border-top: 5px solid {theme_color}; max-width: 1000px; margin: auto; }}
            .predict-box {{ 
                background: linear-gradient(135deg, #1e2530 0%, #2c3e50 100%); 
                padding: 30px; border-radius: 12px; margin: 20px 0; text-align: center; 
                border: 1px solid #3e4b5b; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            }}
            .milestone-label {{ color: #bdc3c7; font-size: 14px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }}
            .milestone-value {{ font-size: 32px; font-weight: 800; color: #ffffff; text-shadow: 0 0 15px rgba(255,255,255,0.3); margin-bottom: 25px; }}
            
            .predict-grid {{ 
                display: flex; justify-content: space-between; gap: 20px;
                border-top: 1px solid rgba(255,255,255,0.1); padding-top: 25px; 
            }}
            .predict-item {{ flex: 1; text-align: center; }}
            .predict-label {{ color: #888; font-size: 13px; margin-bottom: 8px; }}
            .highlight {{ color: #f1c40f; font-size: 20px; font-weight: bold; font-family: 'Courier New', monospace; }}
            
            .days-badge {{ 
                display: inline-block; margin-top: 10px; background: rgba(255,255,255,0.1); 
                padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #ddd; 
            }}
            
            /* 统一右上角数据样式 */
            .stat-label {{ color:#888; font-size:12px; margin-bottom: 2px; }}
            .stat-value-group {{ margin-bottom: 10px; }}
            .stat-value-main {{ font-size: 24px; font-weight: 700; font-family: 'Segoe UI', Roboto, sans-serif; }}
            .color-station {{ color: {station_color}; }}
            .color-highway {{ color: #eee; }}

            button {{
                margin: 0 2px; padding: 4px 10px; background: #1e2530; color: #eee;
                border: 1px solid #3e4b5b; border-radius: 4px; cursor: pointer; transition: 0.2s;
            }}
            button:hover {{ background: #3e4b5b; }}
            button.active {{
                background: {theme_color};
                border-color: {theme_color};
                color: #fff;
                box-shadow: 0 0 10px rgba(0, 163, 224, 0.5);
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2 style="margin:0; font-weight: 300; letter-spacing: 1px;">NIO Power <span style="font-weight:700;">INSIGHT</span></h2>
            
            <div style="margin: 20px 0; display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div class="stat-label">实时累计换电总数</div>
                    <div style="font-size: 38px; font-weight: 800; color: {theme_color}; line-height: 1;">{latest_count:,}</div>
                </div>
                <div style="text-align: right;">
                    <div class="stat-value-group">
                        <div class="stat-label">换电站总数</div>
                        <div class="stat-value-main color-station">{int(latest['站数']) if not pd.isna(latest['站数']) else '--'}</div>
                    </div>
                    <div class="stat-value-group">
                        <div class="stat-label">高速换电站</div>
                        <div class="stat-value-main color-highway">{latest_highway_stations}</div>
                    </div>
                </div>
            </div>
            
            <div class="predict-box">
                <div class="milestone-label">🏁 下一个里程碑目标</div>
                <div class="milestone-value">{next_milestone:,} <span style="font-size:16px; font-weight:300;">次</span></div>
                
                <div class="predict-grid">
                    <div class="predict-item" style="border-right: 1px solid rgba(255,255,255,0.1);">
                        <div class="predict-label">近期线性预测 (精准时刻)</div>
                        <div class="highlight">{pred_time_str}</div>
                        <div class="days-badge">距离达成约剩 <b style="color:#fff;">{days_left_linear}</b> 天</div>
                    </div>
                    <div class="predict-item">
                        <div class="predict-label">历史趋势预测 (加速模型)</div>
                        <div class="highlight" style="color: #2ecc71;">{trend_pred_str}</div>
                        <div class="days-badge">距离达成约剩 <b style="color:#fff;">{days_left_trend}</b> 天</div>
                    </div>
                </div>
            </div>

            <div style="margin:10px 0 10px 0; text-align:right; font-size:12px;">
                <span style="margin-right:8px; color:#888;">缩放区间:</span>
                <button onclick="nioSetRange(24, 'hours')" id="btn-24h">24小时</button>
                <button onclick="nioSetRange(7, 'days')" id="btn-7d">7天</button>
                <button onclick="nioSetRange(30, 'days')" id="btn-30d">30天</button>
                <button onclick="nioSetRange(90, 'days')" id="btn-90d">90天</button>
                <button onclick="nioShowAll()" id="btn-all">全部</button>
            </div>
            
            <div style="background:#000; padding:10px; border-radius:10px; border: 1px solid #222;">
                {fig.to_html(full_html=False, include_plotlyjs='cdn')}
            </div>
        </div>

        <script>
        const NIO_PREV_MILESTONE = {prev_milestone};
        const NIO_PREV_PREV_MILESTONE = {prev_prev_milestone};
        const NIO_LATEST_COUNT = {latest_count};

        function getPlotlyDiv() {{
            return document.querySelector('.plotly-graph-div');
        }}

        function setActiveButton(btnId) {{
            document.querySelectorAll('button[id^="btn-"]').forEach(btn => btn.classList.remove('active'));
            const btn = document.getElementById(btnId);
            if (btn) btn.classList.add('active');
        }}

        window.nioSetRange = function(value, unit) {{
            const plotDiv = getPlotlyDiv();
            if (!plotDiv || typeof Plotly === 'undefined') return;

            let latestTime = 0;
            plotDiv.data.forEach(trace => {{
                if (trace.x && trace.x.length > 0) {{
                    const times = trace.x.map(t => new Date(t).getTime());
                    const max = Math.max(...times);
                    if (max > latestTime) latestTime = max;
                }}
            }});

            const endTime = latestTime > 0 ? latestTime : new Date().getTime();
            const ms = unit === 'hours' ? value * 3600000 : value * 86400000;
            const startTime = endTime - ms;

            const update = {{
                'xaxis.range': [new Date(startTime).toISOString(), new Date(endTime).toISOString()]
            }};

            if ((value === 7 || value === 24 && unit === 'hours') && NIO_LATEST_COUNT > NIO_PREV_MILESTONE) {{
                update['yaxis.range'] = [NIO_PREV_MILESTONE, NIO_LATEST_COUNT * 1.005];
                update['yaxis.autorange'] = false;
            }} else if ((value === 30 || value === 90) && NIO_LATEST_COUNT > NIO_PREV_MILESTONE) {{
                update['yaxis.range'] = [NIO_PREV_PREV_MILESTONE, NIO_LATEST_COUNT * 1.005];
                update['yaxis.autorange'] = false;
            }} else {{
                update['yaxis.autorange'] = true;
            }}

            update['yaxis2.autorange'] = true;
            Plotly.relayout(plotDiv, update);

            // 更新按钮状态
            if (unit === 'hours') {{
                setActiveButton('btn-24h');
            }} else {{
                setActiveButton('btn-' + value + 'd');
            }}
        }};

        window.nioShowAll = function() {{
            const plotDiv = getPlotlyDiv();
            if (plotDiv) {{
                Plotly.relayout(plotDiv, {{
                    'xaxis.autorange': true,
                    'yaxis.autorange': true,
                    'yaxis2.autorange': true
                }});
                setActiveButton('btn-all');
            }}
        }};
        </script>
    </body>
    </html>
    """
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == "__main__":
    run_analysis()
