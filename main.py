import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from notion_client import Client

# 读取 GitHub Secrets 里的环境变量
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
REPO = os.getenv("GITHUB_REPOSITORY")

# 目标网页
CME_URL = "https://www.cmegroup.com/solutions/clearing/operations-and-deliveries/nymex-delivery-notices.html"

def run():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    
    print("正在访问 CME Delivery Notices 网站...")
    try:
        response = requests.get(CME_URL, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"访问 CME 网站失败: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')

    # ========== 核心修改点：根据你提供的线索，直接抓取文件名 ==========
    file_url = None
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.text.strip().lower()
        
        # 如果链接的 href 里包含 'MetalsIssuesAndStopsReport'，或者链接文字就是 'daily' 且包含金属相关路径
        if 'metalsissuesandstopsreport' in href.lower() or (text == 'daily' and 'notices' in href.lower()):
            file_url = href
            # 补全绝对路径
            if file_url.startswith('/'):
                file_url = "https://www.cmegroup.com" + file_url
            break

    if not file_url:
        print("未能在网页上找到 MetalsIssuesAndStopsReport 的下载链接，可能今天尚未更新。")
        return

    print(f"找到文件链接: {file_url}")

    # 下载文件
    # CME的链接可能是 .pdf 或 .txt，这里动态获取真实的文件名
    filename = file_url.split('/')[-1]
    
    # 如果URL没有明显文件名，我们给它强制命名
    if "MetalsIssuesAndStops" not in filename:
        filename = "MetalsIssuesAndStopsReport.pdf" 
        
    print(f"正在下载文件: {filename}...")
    try:
        file_resp = requests.get(file_url, headers=headers, timeout=15)
        file_resp.raise_for_status()
    except Exception as e:
        print(f"下载文件失败: {e}")
        return

    os.makedirs("downloads", exist_ok=True)
    filepath = f"downloads/{filename}"

    with open(filepath, 'wb') as f:
        f.write(file_resp.content)
    print(f"文件已下载到: {filepath}")

    # 获取下载当天的日期
    report_date = datetime.now().strftime("%Y-%m-%d")
    print(f"使用的下载日期: {report_date}")

    raw_github_url = f"https://raw.githubusercontent.com/{REPO}/main/{filepath}"

    # 更新 Notion Database
    print("正在写入 Notion...")
    notion = Client(auth=NOTION_TOKEN)
    
    # 我注意到你的截图里，最左侧的 Name 列是空的，所以这里我依然填入文件名，但如果你想让它像截图一样保持空白，
    # 可以把 "content": filename 改成 "content": ""
    new_page = {
        "Name": {"title": [{"text": {"content": filename}}]},       
        "Period": {"select": {"name": "Daily"}},                    # 填入 Period 
        "Date": {"date": {"start": report_date}},                   # 填入 Date 
        "Files & media": {                                          # 填入 Files & media 
            "files": [
                {
                    "name": filename, 
                    "type": "external", 
                    "external": {"url": raw_github_url}
                }
            ]
        }
    }

    try:
        notion.pages.create(parent={"database_id": DATABASE_ID}, properties=new_page)
        print("🎉 成功添加到新 Notion 表格！")
    except Exception as e:
        print(f"写入 Notion 时出错: {e}")

if __name__ == "__main__":
    run()
