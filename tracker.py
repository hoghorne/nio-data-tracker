import csv
import os
import time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# 蔚来换电地图主页
URL = "https://www.nio.cn/charger-map"

def get_nio_data():
    """使用 Playwright 模拟浏览器抓取并拼接数字"""
    results = []
    
    with sync_playwright() as p:
        # 1. 启动 Chromium 浏览器 (无头模式)
        browser = p.chromium.launch(headless=True)
        # 伪装成真实的桌面浏览器
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # 2. 访问页面并等待网络空闲
            print(f"正在访问: {URL}")
            page.goto(URL, wait_until="networkidle", timeout=60000)
            
            # 等待 5 秒确保数字滚动动画加载完成
            page.wait_for_timeout(5000)

            # 定义内部抓取逻辑
            def capture_current_frame():
                # 计算北京时间 (UTC+8)
                beijing_now = datetime.now(timezone.utc) + timedelta(hours=8)
                
                # 抓取函数：根据截图中的结构提取每一个数字 <li> 中的 <span> 并拼接
                def extract_val(label_text):
                    # 选择器逻辑：找到包含项目名称的 h6，定位到其后的数字翻转区域，提取所有数字
                    selector = f"h6:has-text('{label_text}') + div .pe-biz-digit-flip li span"
                    elements = page.query_selector_all(selector)
                    # 过滤出纯数字并拼成字符串
                    return "".join([el.inner_text() for el in elements if el.inner_text().isdigit()])

                swap_count = extract_val("实时累计换电次数")
                total_stations = extract_val("蔚来能源换电站")
                highway_stations = extract_val("高速公路换电站")

                # 星期转换
                weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
                weekday_cn = weekdays[beijing_now.weekday()]

                return [
                    beijing_now.strftime("%Y-%m-%d %H:%M:%S"),
                    weekday_cn,
                    swap_count,
                    total_stations,
                    highway_stations
                ]

            # 3. 连续采集 10 秒，每 2 秒存一次数据 (共 5 组)
            print("开始高频采集（持续约10秒）...")
            for i in range(5):
                frame_data = capture_current_frame()
                if frame_data[2]:  # 只要“换电次数”抓到了就视为成功
                    results.append(frame_data)
                    print(f"采集成功 [{i+1}/5]: {frame_data[2]}")
                else:
                    print(f"采集提示 [{i+1}/5]: 尚未检测到数字，重试中...")
                time.sleep(2)

        except Exception as e:
            print(f"❌ 运行过程中发生错误: {e}")
        finally:
            browser.close()
            
    return results

def save_to_csv(rows):
    """保存数据到 CSV，支持 Excel 中文不乱码"""
    if not rows:
        print("⚠️ 没有采集到有效数据，跳过写入。")
        return
    
    file_path = 'nio_swaps.csv'
    file_exists = os.path.isfile(file_path)
    
    # 使用 utf-8-sig 确保 Windows Excel 直接打开不乱码
    with open(file_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # 如果是第一次创建文件，写入中文表头
        if not file_exists:
            writer.writerow(['记录时间', '星期', '实时累计换电次数', '蔚来能源换电站', '高速公路换电站'])
        writer.writerows(rows)

if __name__ == "__main__":
    captured_data = get_nio_data()
    save_to_csv(captured_data)
    print(f"✅ 脚本运行结束。本次共存入 {len(captured_data)} 行数据。")
