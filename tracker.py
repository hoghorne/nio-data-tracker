import csv
import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

def get_nio_data():
    with sync_playwright() as p:
        # 启动 Chromium 浏览器
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        page = context.new_page()
        
        try:
            # 访问网页
            page.goto("https://www.nio.cn/charger-map", wait_until="networkidle")
            # 等待 5 秒，确保数字翻页动画完成
            page.wait_for_timeout(5000)

            # 抓取数据函数：定位到对应的标题，然后找它下面的数字列表
            def extract_val(label_text):
                # 定位包含标题的 h6，然后找到它同级的数字区域
                selector = f"h6:has-text('{label_text}') + div .pe-biz-digit-flip li span"
                elements = page.query_selector_all(selector)
                # 把每个 li 里的数字字符拼起来
                return "".join([el.inner_text() for el in elements if el.inner_text().isdigit()])

            swap_count = extract_val("实时累计换电次数")
            total_stations = extract_val("蔚来能源换电站")
            highway_stations = extract_val("高速公路换电站")

            now = datetime.now()
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            weekday_cn = weekdays[now.weekday()]

            browser.close()
            return [timestamp, weekday_cn, swap_count, total_stations, highway_stations]
        except Exception as e:
            print(f"抓取失败: {e}")
            browser.close()
            return None

def save_to_csv(rows):
    file_path = 'nio_swaps.csv'
    file_exists = os.path.isfile(file_path)
    with open(file_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['记录时间', '星期', '实时累计换电次数', '蔚来能源换电站', '高速公路换电站'])
        writer.writerows(rows)

if __name__ == "__main__":
    # 为了满足你“按秒”的需求，我们一次运行采集 30 秒的数据（每 5 秒采一次）
    all_data = []
    print("开始通过模拟浏览器采集数据...")
    for i in range(6):
        data = get_nio_data()
        if data and data[2]: # 确保抓到了数字
            all_data.append(data)
            print(f"进度 {i+1}/6: 抓取到 {data[2]}")
        time.sleep(5) # 间隔 5 秒
    
    if all_data:
        save_to_csv(all_data)
