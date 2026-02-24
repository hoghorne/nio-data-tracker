import csv
import os
import time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# 目标地址
URL = "https://chargermap.nio.com/pe/h5/static/chargermap?channel=official"

def get_nio_data():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        try:
            print(f"正在访问: {URL}")
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            
            # 等待核心容器加载
            print("等待数据组件加载...")
            page.wait_for_selector(".pe-biz-digit-flip", timeout=30000)
            time.sleep(3)

            def capture_current_frame():
                beijing_now = datetime.now(timezone.utc) + timedelta(hours=8)
                
                # 针对不同结构的两套提取逻辑
                def extract_val(label_text):
                    # --- 逻辑 1: 针对“实时累计换电次数” (li > span 结构) ---
                    flip_selector = f"h6:has-text('{label_text}') + div .pe-biz-digit-flip li span"
                    elements = page.query_selector_all(flip_selector)
                    if elements:
                        return "".join([el.inner_text() for el in elements if el.inner_text().strip().isdigit()])
                    
                    # --- 逻辑 2: 针对“换电站数量” (strong 标签结构) ---
                    # 寻找包含标题的 h6 旁边的 strong 标签
                    strong_selector = f"h6:has-text('{label_text}') + strong"
                    strong_element = page.query_selector(strong_selector)
                    if strong_element:
                        # 提取文本并去掉逗号
                        return strong_element.inner_text().replace(',', '').strip()
                    
                    return "0"

                # 注意：截图显示标题是“其中高速公路换电站”，所以我们要用全名
                swap_count = extract_val("实时累计换电次数")
                total_stations = extract_val("蔚来能源换电站")
                highway_stations = extract_val("其中高速公路换电站")

                weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
                return [
                    beijing_now.strftime("%Y-%m-%d %H:%M:%S"),
                    weekdays[beijing_now.weekday()],
                    swap_count,
                    total_stations,
                    highway_stations
                ]

            print("开始高频采集...")
            for i in range(5):
                frame_data = capture_current_frame()
                if frame_data[2] != "0":
                    results.append(frame_data)
                    print(f"采集成功 [{i+1}/5]: 换电{frame_data[2]}, 总站{frame_data[3]}, 高速{frame_data[4]}")
                else:
                    print(f"采集提示 [{i+1}/5]: 数据尚未就绪...")
                time.sleep(2)

        except Exception as e:
            print(f"❌ 运行错误: {e}")
        finally:
            browser.close()
            
    return results

def save_to_csv(rows):
    if not rows:
        print("⚠️ 未采集到有效数据。")
        return
    file_path = 'nio_swaps.csv'
    file_exists = os.path.isfile(file_path)
    with open(file_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['记录时间', '星期', '实时累计换电次数', '蔚来能源换电站', '高速公路换电站'])
        writer.writerows(rows)

if __name__ == "__main__":
    captured_data = get_nio_data()
    save_to_csv(captured_data)
    print(f"✅ 脚本结束。")
