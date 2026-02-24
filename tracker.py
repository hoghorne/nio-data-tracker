import requests
import re
import csv
import os
from datetime import datetime

# 目标：蔚来官网充电地图主页
URL = "https://www.nio.cn/charger-map"

def get_nio_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    
    try:
        # 1. 获取网页原文
        response = requests.get(URL, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        html_content = response.text
        
        # 2. 定义搜索函数 (直接寻找中文标签后面的数字)
        def search_number(label):
            # 这个正则会寻找： 标签名字，后面跟着任意字符，直到遇到一串数字
            # 兼容 73,123,456 这种带逗号的格式
            pattern = f"{label}.*?([\d,]+)"
            match = re.search(pattern, html_content)
            if match:
                num_str = match.group(1).replace(',', '')
                return num_str
            return "N/A"

        # 3. 抓取你要求的三个数据
        swap_count = search_number("实时累计换电次数")
        total_stations = search_number("蔚来能源换电站")
        highway_stations = search_number("高速公路换电站")

        # 获取时间
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday_cn = weekdays[now.weekday()]

        return [timestamp, weekday_cn, swap_count, total_stations, highway_stations]

    except Exception as e:
        print(f"❌ 抓取异常: {e}")
        return None

def save_to_csv(row):
    file_path = 'nio_swaps.csv'
    file_exists = os.path.isfile(file_path)
    with open(file_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['记录时间', '星期', '实时累计换电次数', '蔚来能源换电站', '高速公路换电站'])
        writer.writerow(row)

if __name__ == "__main__":
    result = get_nio_data()
    if result:
        save_to_csv(result)
        print(f"✅ 抓取成功: {result}")
    else:
        # 如果失败，存入一条错误记录，确保 Git 有内容可以提交
        error_row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "-", "抓取失败", "-", "-"]
        save_to_csv(error_row)
        print("❌ 抓取失败，已记录错误日志")
