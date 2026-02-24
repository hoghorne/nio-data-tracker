import requests
import re
import csv
import os
from datetime import datetime

# 蔚来换电地图页面
URL = "https://www.nio.cn/charger-map"

def get_nio_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9"
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=20)
        # 强制设置编码为 utf-8，确保中文不乱码
        response.encoding = 'utf-8'
        html_text = response.text

        # 使用正则表达式直接匹配中文项目后面的数字
        # 解释：查找“项目名称”，跳过一些符号，抓取后面的数字
        def extract_number(label):
            # 匹配模式：项目名称 + 可能是引号/冒号/空格 + 数字
            pattern = f'"{label}"\s*:\s*"?([\d,]+)"?'
            match = re.search(pattern, html_text)
            if not match:
                # 备用方案：如果不是JSON格式，尝试匹配 HTML 标签内的模式
                pattern = f'{label}.*?>([\d,]+)<'
                match = re.search(pattern, html_text)
            
            if match:
                # 去掉数字里的逗号，转为纯数字
                return match.group(1).replace(',', '')
            return "N/A"

        swap_count = extract_number("实时累计换电次数")
        total_stations = extract_number("蔚来能源换电站")
        highway_stations = extract_number("高速公路换电站")

        # 获取时间
        now = datetime.now()
        # 格式：2023-11-27 14:05:01
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        # 增加星期显示（中文）
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday_cn = weekdays[now.weekday()]

        return [timestamp, weekday_cn, swap_count, total_stations, highway_stations]

    except Exception as e:
        print(f"抓取发生错误: {e}")
        return None

def save_to_csv(row):
    file_exists = os.path.isfile('nio_swaps.csv')
    # utf-8-sig 编码可以让 Excel 直接双击打开不乱码
    with open('nio_swaps.csv', 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # 如果是新文件，先写表头
        if not file_exists:
            writer.writerow(['记录时间', '星期', '实时累计换电次数', '蔚来能源换电站', '高速公路换电站'])
        writer.writerow(row)

if __name__ == "__main__":
    data = get_nio_data()
    if data:
        print(f"抓取到的数据: {data}")
        save_to_csv(data)
