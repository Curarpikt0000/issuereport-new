import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from notion_client import Client

# 读取 GitHub Secrets 里的环境变量
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
REPO = os.getenv("GITHUB_REPOSITORY")

# 这次新的目标网页
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

    # 寻找包含 "Metal Delivery Notices" 和 "daily" 的文件链接
    file_url = None
    for a in soup.find_all('a', href=True):
        text = a.text.lower()
        if 'metal delivery notices' in text and 'daily' in text:
            file_url = a['href']
            if file_url.startswith('/'):
                file_url = "https://www.cmegroup.com" + file_url
            break

    if not file_url:
        print("未能在网页上找到 COMEX & NYMEX Metal Delivery Notices daily 的链接。")
        return

    print(f"找到文件链接: {file_url}")

    # 下载文件
    filename = file_url.split('/')[-1]
    print("正在下载文件...")
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
    
    new_page = {
        "Name": {"title": [{"text": {"content": filename}}]},       # 填入最左侧 Name 列
        "Period": {"select": {"name": "Daily"}},                    # 填入 Period 列（设定为 Daily）
        "Date": {"date": {"start": report_date}},                   # 填入 Date 列（下载日期）
        "Files & media": {                                          # 填入你截图里的 Files & media 列
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
