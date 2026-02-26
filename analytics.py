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
        # 读取 CSV 并清洗列名
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        df.columns = [c.strip().replace('\ufeff', '') for c in df.columns]
    except Exception as e:
        print(f"Read CSV Error: {e}"); return

    # 标准化列名映射
    mapping = {
        '记录时间': '时间', '时间': '时间',
        '实时累计换电次数': '次数'
    }
    for old_name, new_name in mapping.items():
        if old_name in df.columns:
            df.rename(columns={old_name: new_name}, inplace=True)

    # 转换数字格式
    def clean_num(value):
        if pd.isna(value): return value
        if isinstance(value, str):
            return value.replace(',', '').replace('"', '').replace(' ', '').strip()
        return value

    if '次数' in df.columns:
        df['次数'] = df['次数'].apply(clean_num)
        df['次数'] = pd.to_numeric(df['次数'], errors='coerce')
    
    df = df.dropna(subset=['次数', '时间'])
    df['时间'] = pd.to_datetime(df['时间'])
    df = df.sort_values('时间')

    if df.empty: return

    # --- 基础统计 ---
    latest_record = df.iloc[-1]
    latest_count = int(latest_record['次数'])
    
    # 1. 自动计算下一个里程碑 (每 10,000,000 为一级)
    milestone_step = 10000000
    next_milestone = ((latest_count // milestone_step) + 1) * milestone_step

    # 2. 72 小时趋势预测逻辑
    # 寻找约 72 小时前的记录
    lookback_days = 3
    target_time = latest_record['时间'] - timedelta(days=lookback_days)
    df_history = df[df['时间'] <= target_time]
    
    # 如果数据不足 72 小时，尝试寻找最早的一条记录
    if df_history.empty:
        old_record = df.iloc[0]
    else:
        old_record = df_history.iloc[-1]

    # 计算时间差和次数差
    time_diff = latest_record['时间'] - old_record['时间']
    time_diff_hours = time_diff.total_seconds() / 3600
    count_diff = latest_count - old_record['次数']

    if time_diff_hours > 0.1: # 确保有足够的时间跨度
        # 计算每秒换电速率
        rate_per_second = count_diff / time_diff.total_seconds()
        # 日均速率 (仅用于显示)
        rate_per_day = rate_per_second * 86400
        
        # 计算剩余量和预计达成时间
        remaining_swaps = next_milestone - latest_count
        seconds_to_go = remaining_swaps / rate_per_second
        
        predicted_dt = latest_record['时间'] + timedelta(seconds=seconds_to_go)
        
        # 格式化输出：2026-02-25 00:10:23
        predicted_time_str = predicted_dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # 计算倒计时天数（带1位小数展示）
        days_to_go_str = f"{seconds_to_go / 86400:.1f}"
    else:
        rate_per_day = 0
        predicted_time_str = "计算中..."
        days_to_go_str = "--"

    # 3. 计算每日增量 (用于图表)
    all_dates = sorted(df['时间'].dt.date.unique())
    daily_data = []
    for i, date in enumerate(all_dates):
        df_date = df[df['时间'].dt.date == date]
        if df_date.empty: continue
        first_val = df_date.iloc[0]['次数']
        if i < len(all_dates) - 1:
            next_df = df[df['时间'].dt.date >= all_dates[i+1]]
            day_swaps = int(next_df.iloc[0]['次数'] - first_val) if not next_df.empty else 0
            is_est = False
        else:
            t_delta = (df_date.iloc[-1]['时间'] - df_date.iloc[0]['时间']).total_seconds() / 3600
            day_swaps = int((df_date.iloc[-1]['次数'] - first_val) / t_delta * 24) if t_delta > 0.1 else 0
            is_est = True
        daily_data.append({'日期': date.strftime('%Y-%m-%d'), '增量': day_swaps, '状态': '推算' if is_est else '完成'})

    df_daily = pd.DataFrame(daily_data)

    # --- 可视化 ---
    theme_color = "#00A3E0"
    
    # 图 1: 累计趋势
    fig1 = px.line(df, x='时间', y='次数', template='plotly_dark')
    fig1.update_traces(line=dict(color=theme_color, width=3))
    fig1.update_yaxes(autorange=True, tickformat=",d", gridcolor='#333', rangemode="normal")
    fig1.update_layout(title="累计换电趋势", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10,r=10,t=40,b=10))

    # 图 2: 日增量
    fig2 = px.bar(df_daily.tail(15), x='日期', y='增量', template='plotly_dark', color='状态', 
                  color_discrete_map={'推算': '#555', '完成': '#2ecc71'})
    fig2.update_layout(title="最近 15 天日增量统计", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10,r=10,t=40,b=10), showlegend=False)

    # --- 生成 HTML ---
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ background: #0b0e14; color: white; font-family: -apple-system, sans-serif; padding: 15px; }}
            .card {{ background: #1a1f28; padding: 20px; border-radius: 15px; border-top: 5px solid {theme_color}; max-width: 900px; margin: auto; }}
            .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 15px; }}
            .stat-box {{ background: #252b36; padding: 15px; border-radius: 10px; }}
            .prediction-card {{ background: linear-gradient(135deg, #1e2530 0%, #2c3e50 100%); padding: 25px; border-radius: 12px; margin: 20px 0; border: 1px solid #3e4b5b; text-align: center; }}
            .label {{ color: #999; font-size: 13px; margin-bottom: 5px; }}
            .value {{ font-size: 24px; font-weight: bold; color: {theme_color}; }}
            .highlight {{ color: #f1c40f; font-size: 22px; font-weight: bold; font-family: 'Courier New', Courier, monospace; }}
            .chart-box {{ margin-top: 20px; background: #111; padding: 10px; border-radius: 10px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2 style="margin:0 0 15px 0; font-size: 22px;">NIO 换电实时监控与预测</h2>
            
            <div class="stat-box" style="text-align:center;">
                <div class="label">实时累计换电总数</div>
                <div style="font-size: 38px; font-weight: bold; letter-spacing: 1px;">{latest_count:,}</div>
                <div style="color:#555; font-size:12px;">数据同步至: {latest_record['时间'].strftime('%Y-%m-%d %H:%M:%S')}</div>
            </div>

            <div class="stats-grid">
                <div class="stat-box">
                    <div class="label">72h 平均增速</div>
                    <div class="value">{int(rate_per_day/24):,} <span style="font-size:14px;">次/时</span></div>
                </div>
                <div class="stat-box">
                    <div class="label">预计日均增量</div>
                    <div class="value" style="color:#2ecc71;">{int(rate_per_day):,} <span style="font-size:14px;">次/日</span></div>
                </div>
            </div>

            <div class="prediction-card">
                <div style="color:#bdc3c7; font-size:14px;">目标里程碑：<b style="color:white; font-size:16px;">{next_milestone:,} 次</b></div>
                <div style="margin: 15px 0;">
                    <div class="label">预计达成精确时间</div>
                    <div class="highlight">{predicted_time_str}</div>
                </div>
                <div style="font-size: 15px; color: #bdc3c7;">
                    距离达成约剩 <span style="color:white; font-weight:bold;">{days_to_go_str}</span> 天
                </div>
                <div style="color:#666; font-size:11px; margin-top:12px;">* 预测逻辑：基于过去 72 小时平均换电斜率动态推算</div>
            </div>

            <div class="chart-box">{fig1.to_html(full_html=False, include_plotlyjs='cdn')}</div>
            <div class="chart-box">{fig2.to_html(full_html=False, include_plotlyjs='cdn')}</div>
        </div>
    </body>
    </html>
    """
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == "__main__":
    run_analysis()
