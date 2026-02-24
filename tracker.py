import csv
import os
import time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

URL = "https://chargermap.nio.com/pe/h5/static/chargermap?channel=official"

def get_nio_data():
    results = []
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=True)
        # 增加更多的伪装参数，防止被识别为机器人
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        try:
            print(f"正在访问: {URL}")
            # 修改点1：使用 commit 模式，只要网页开始下载就不再阻塞
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            
            # 修改点2：明确等待数字区域出现，而不是等整个网页网络空闲
            # 我们等截图里那个包含数字的类名出现
            print("等待数据组件加载...")
            page.wait_for_selector(".pe-biz-digit-flip", timeout=30000)
            
            # 额外再停 3 秒，确保翻页动画完成
            time.sleep(3)

            def capture_current_frame():
                beijing_now = datetime.now(timezone.utc) + timedelta(hours=8)
                
                def extract_val(label_text):
                    # 修改点3：优化选择器，确保能精准定位
                    selector = f"h6:has-text('{label_text}') + div .pe-biz-digit-flip li span"
                    elements = page.query_selector_all(selector)
                    val = "".join([el.inner_text() for el in elements if el.inner_text().strip().isdigit()])
                    return val if val else "0"

                swap_count = extract_val("实时累计换电次数")
                total_stations = extract_val("蔚来能源换电站")
                highway_stations = extract_val("高速公路换电站")

                weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
                weekday_cn = weekdays[beijing_now.weekday()]

                return [
                    beijing_now.strftime("%Y-%m-%d %H:%M:%S"),
                    weekday_cn,
                    swap_count,
                    total_stations,
                    highway_stations
                ]

            print("开始高频采集...")
            for i in range(5):
                frame_data = capture_current_frame()
                # 只要换电次数不是"0"且不是空，就记录
                if frame_data[2] != "0":
                    results.append(frame_data)
                    print(f"采集成功 [{i+1}/5]: {frame_data[2]}")
                else:
                    print(f"采集提示 [{i+1}/5]: 数据尚未就绪...")
                time.sleep(2)

        except Exception as e:
            print(f"❌ 运行错误: {e}")
            # 即使报错，我们也截图存证（可选，方便调试）
            # page.screenshot(path="error_debug.png")
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
    print(f"✅ 脚本结束。存入 {len(captured_data)} 行。")
