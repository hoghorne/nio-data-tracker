import csv
import os
import time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# 蔚来换电地图 H5 接口地址
URL = "https://chargermap.nio.com/pe/h5/static/chargermap?channel=official"

def get_nio_data():
    results = []
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        try:
            print(f"正在访问北京时间 2026 数据源: {URL}")
            # 只要 HTML 骨架加载完成即开始执行，提高响应速度
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            
            print("等待数字组件渲染...")
            # 确保数字翻转组件已出现在页面上
            page.wait_for_selector(".pe-biz-digit-flip", timeout=30000)
            # 额外等待以确保 JS 动画完成初始赋值
            time.sleep(5)

            def capture_current_frame():
                # 校准北京时间 (UTC+8)
                beijing_now = datetime.now(timezone.utc) + timedelta(hours=8)
                
                def extract_val(label_text):
                    # --- 针对“换电次数”的多位滚动结构处理 ---
                    container_selector = f"h6:has-text('{label_text}') + div ul.pe-biz-digit-flip"
                    container = page.query_selector(container_selector)
                    
                    if container:
                        # 找到代表每一位数字的 li 容器
                        digits_li = container.query_selector_all("li")
                        final_num_str = ""
                        for li in digits_li:
                            # 蔚来该组件在跳变时，li 下会存在多个 span。
                            # 目标数字通常是该槽位中最后插入或最末尾的 span
                            spans = li.query_selector_all("span")
                            valid_digits = [s.inner_text().strip() for s in spans if s.inner_text().strip().isdigit()]
                            if valid_digits:
                                # 只取当前槽位中确定的最后一个数字字符
                                final_num_str += valid_digits[-1]
                        return final_num_str

                    # --- 针对“换电站数量”的静态结构处理 ---
                    strong_selector = f"h6:has-text('{label_text}') + strong"
                    strong_element = page.query_selector(strong_selector)
                    if strong_element:
                        return strong_element.inner_text().replace(',', '').strip()
                    
                    return "0"

                # 提取三个核心维度
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

            print("执行高频校验采集...")
            for i in range(5):
                frame_data = capture_current_frame()
                num_str = frame_data[2]
                
                # --- 优化的长度校验逻辑 ---
                # 允许从 9 位（亿级）跳转到 10 位或 11 位（十亿/百亿级）
                # 但拒绝由于抓取重复导致的 12 位及以上数据
                if num_str and 8 < len(num_str) < 12:
                    results.append(frame_data)
                    print(f"成功记录 [{i+1}/5]: {num_str}")
                else:
                    print(f"检测到异常数据长度 ({len(num_str) if num_str else 0}), 自动丢弃: {num_str}")
                
                time.sleep(2)

        except Exception as e:
            print(f"❌ 运行异常: {e}")
        finally:
            browser.close()
            
    return results

def save_to_csv(rows):
    if not rows:
        print("⚠️ 未能采集到符合质量标准的数据。")
        return
    file_path = 'nio_swaps.csv'
    file_exists = os.path.isfile(file_path)
    # 使用 utf-8-sig 确保 Excel 直接打开中文不乱码
    with open(file_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['记录时间', '星期', '实时累计换电次数', '蔚来能源换电站', '高速公路换电站'])
        writer.writerows(rows)

if __name__ == "__main__":
    captured_data = get_nio_data()
    save_to_csv(captured_data)
    print(f"✅ 任务流程结束。")
