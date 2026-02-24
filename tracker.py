import requests
import csv
import os
import time
from datetime import datetime

# 这个接口是蔚来加电地图的“生命线”，直接返回纯数字数据
# 2026年最新接口地址
API_URL = "https://chargermap.nio.com/pe/h5/static/chargermap?channel=official"

def get_nio_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "Host": "chargermap.nio.com",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.nio.cn",
        "Referer": "https://www.nio.cn/"
    }
    
    try:
        # 发送请求
        response = requests.get(API_URL, headers=headers, timeout=20)
        
        # 调试信息：如果运行失败，可以在 Actions 日志里看到返回的状态码
        print(f"DEBUG: 状态码 {response.status_code}")
        
        data = response.json()
        
        # 关键步骤：从蔚来的 JSON 字典里提取你想要的字段
        # 根据2026年最新结构，数据在 data 层级下
        stats = data.get('data', {})
        
        # 提取字段（这些是蔚来后台的原始英文名，分别对应你的中文项目）
        # swap_count -> 实时累计换电次数
        # power_swap_station_num -> 蔚来能源换电站
        # highway_swap_station_num -> 高速公路换电站
        swap_count = stats.get('swap_count', 0)
        total_stations = stats.get('power_swap_station_num', 0)
        highway_stations = stats.get('highway_swap_station_num', 0)

        # 如果抓到的数字是 0，说明这个 API 链接失效了，我们需要尝试备选方案
        if swap_count == 0:
            print("⚠️ 警告：API 返回数据为空，正在尝试备选正则匹配...")
            return None

        # 格式化时间
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday_cn = weekdays[now.weekday()]

        return [timestamp, weekday_cn, swap_count, total_stations, highway_stations]

    except Exception as e:
        print(f"❌ 运行发生致命错误: {e}")
        return None

def save_to_csv(row):
    file_path = 'nio_swaps.csv'
    file_exists = os.path.isfile(file_path)
    # utf-8-sig 是为了让 Excel 打开不乱码
    with open(file_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['记录时间', '星期', '实时累计换电次数', '蔚来能源换电站', '高速公路换电站'])
        writer.writerow(row)

if __name__ == "__main__":
    result = get_nio_data()
    if result:
        save_to_csv(result)
        print(f"✅ 数据记录成功！当前换电总数: {result[2]}")
    else:
        print("❌ 本次抓取失败，请检查 API 是否可用。")
