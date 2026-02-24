import requests
import re
import csv
import os
import time
from datetime import datetime

URL = "https://www.nio.cn/charger-map"

def fetch_once():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.nio.cn/",
        "Accept-Language": "zh-CN,zh;q=0.9"
    }
    try:
        # 获取网页源码
        resp = requests.get(URL, headers=headers, timeout=15)
        resp.encoding = 'utf-8'
        content = resp.text

        # 尝试匹配数字的正则（寻找中文名称后最近的一串数字）
        def extract(label):
            # 匹配 标签名 后面紧跟的任意非数字字符，直到遇到数字
            pattern = f'"{label}"\s*:\s*"?([\d,]+)"?'
            match = re.search(pattern, content)
            if not match:
                # 备选正则：匹配 HTML 标签中的数字
                pattern = f'{label}.*?>([\d,]+)<'
                match = re.search(pattern, content)
            
            if match:
                return match.group(1).replace(',', '')
            return "N/A"

        swap_count = extract("实时累计换电次数")
        total_stations = extract("蔚来能源换电站")
        highway_stations = extract("高速公路换电站")

        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday_cn = weekdays[now.weekday()]

        return [timestamp, weekday_cn, swap_count, total_stations, highway_stations]
    except:
        return None

def save_data():
    file_path = 'nio_swaps.csv'
    file_exists = os.path.isfile(file_path)
    
    # --- 核心修改：按秒记录循环 ---
    # 每次 Actions 启动，连续抓取 60 次，每秒一次
    print("开始秒级采集，持续 60 秒...")
    
    captured_rows = []
    for i in range(60):
        data = fetch_once()
        if data:
            captured_rows.append(data)
            # 在 Actions 日志里实时显示，方便你观察
            print(f"秒级记录 [{i+1}/60]: {data[2]}") 
        time.sleep(1) # 停顿 1 秒

    # 统一写入文件
    with open(file_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['记录时间', '星期', '实时累计换电次数', '蔚来能源换电站', '高速公路换电站'])
        writer.writerows(captured_rows)
    return len(captured_rows)

if __name__ == "__main__":
    count = save_data()
    print(f"✅ 本次运行结束，成功写入 {count} 条秒级数据。")
