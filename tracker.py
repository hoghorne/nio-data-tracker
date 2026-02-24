import requests
import re
import csv
import os
from datetime import datetime

# 目标页面：蔚来充电地图
URL = "https://www.nio.cn/charger-map"

def get_nio_data():
    # 模拟一个非常真实的浏览器环境
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://www.nio.cn/"
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        html = response.text

        # 核心逻辑：直接在源码里找中文关键词旁边的数字
        def find_val(keyword):
            # 这里的正则会寻找： "关键词":"数字" 这种结构
            pattern = f'"{keyword}"\s*:\s*"?([\d,]+)"?'
            match = re.search(pattern, html)
            if match:
                # 提取数字并去掉逗号（例如 100,000,000 变成 100000000）
                return match.group(1).replace(',', '')
            return "0"

        # 对应你要求的三个中文项目
        swap_count = find_val("实时累计换电次数")
        total_stations = find_val("蔚来能源换电站")
        highway_stations = find_val("高速公路换电站")

        # 如果还是抓不到，打印提示，方便在 Actions 日志里查看原因
        if swap_count == "0":
            print("⚠️ 警告：未匹配到关键数据，可能是页面结构变动。")

        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday_cn = weekdays[now.weekday()]

        return [timestamp, weekday_cn, swap_count, total_stations, highway_stations]

    except Exception as e:
        print(f"❌ 运行错误: {e}")
        return None

def save_to_csv(row):
    file_path = 'nio_swaps.csv'
    file_exists = os.path.isfile(file_path)
    with open(file_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            # 这里是你要求的纯中文表头
            writer.writerow(['记录时间', '星期', '实时累计换电次数', '蔚来能源换电站', '高速公路换电站'])
        writer.writerow(row)

if __name__ == "__main__":
    result = get_nio_data()
    if result:
        save_to_csv(result)
        print(f"✅ 数据记录成功：{result}")
