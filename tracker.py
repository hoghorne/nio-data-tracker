import requests
import csv
import time
from datetime import datetime

# 蔚来能源数据接口 (基于公开H5页面分析)
API_URL = "https://chargermap.nio.com/pe/h5/static/chargermap?channel=official"

def get_nio_data():
    try:
        # 模拟浏览器访问
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1"
        }
        # 发送请求获取 JSON 数据
        response = requests.get(API_URL, headers=headers, timeout=10)
        data = response.json()
        
        # 提取关键字段（根据实际API返回结构进行解析）
        # 注意：这里的数据路径可能随官方更新变动，建议定期检查
        stats = data.get('data', {})
        
        cumulative_swaps = stats.get('swap_count', 0)  # 累计换电次数
        total_stations = stats.get('power_swap_station_num', 0) # 能源换电站
        highway_stations = stats.get('highway_swap_station_num', 0) # 高速换电站
        
        # 获取当前时间（北京时间）
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        weekday = now.strftime("%A") # 星期几（英文，如 Monday）
        
        return [timestamp, weekday, cumulative_swaps, total_stations, highway_stations]
    except Exception as e:
        print(f"数据抓取失败: {e}")
        return None

def save_to_csv(row):
    with open('nio_swaps.csv', 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(row)

if __name__ == "__main__":
    new_data = get_nio_data()
    if new_data:
        save_to_csv(new_data)
        print(f"记录成功: {new_data}")
