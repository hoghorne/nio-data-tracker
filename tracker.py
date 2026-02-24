import requests
import csv
import os
from datetime import datetime

# 这是蔚来充电地图官方 H5 页面的后台数据接口，比网页更稳定
API_URL = "https://chargermap.nio.com/pe/h5/static/chargermap?channel=official"

def get_nio_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
        "Referer": "https://www.nio.cn/"
    }
    
    try:
        # 直接请求 JSON 接口
        response = requests.get(API_URL, headers=headers, timeout=20)
        response.raise_for_status() # 如果请求失败会报错
        res_json = response.json()
        
        # 蔚来接口返回的数据结构在 data 字段中
        # 根据官方接口字段映射：
        # swap_count -> 实时累计换电次数
        # power_swap_station_num -> 蔚来能源换电站
        # highway_swap_station_num -> 高速公路换电站
        data_block = res_json.get('data', {})
        
        swap_count = data_block.get('swap_count', "0")
        total_stations = data_block.get('power_swap_station_num', "0")
        highway_stations = data_block.get('highway_swap_station_num', "0")

        # 获取当前北京时间
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # 星期转换
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday_cn = weekdays[now.weekday()]

        # 返回我们要存入 CSV 的这一行
        return [timestamp, weekday_cn, swap_count, total_stations, highway_stations]

    except Exception as e:
        print(f"数据获取失败，错误原因: {e}")
        return None

def save_to_csv(row):
    file_path = 'nio_swaps.csv'
    file_exists = os.path.isfile(file_path)
    
    # utf-8-sig 编码确保 Excel 打开中文不乱码
    with open(file_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # 如果是新文件，先写入中文表头
        if not file_exists:
            writer.writerow(['记录时间', '星期', '实时累计换电次数', '蔚来能源换电站', '高速公路换电站'])
        writer.writerow(row)

if __name__ == "__main__":
    result = get_nio_data()
    if result:
        save_to_csv(result)
        print(f"✅ 成功记录数据: {result}")
    else:
        print("❌ 本次未抓取到有效数据")
