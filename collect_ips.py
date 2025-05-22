import requests
import re
import os
import zipfile
from io import BytesIO
from bs4 import BeautifulSoup
import chardet

# 目标URL列表及其类型（html/text/zip）
url_info = [
    {'url': 'https://ip.164746.xyz', 'type': 'html'},
    {'url': 'https://raw.githubusercontent.com/ymyuuu/IPDB/refs/heads/main/BestCF/bestcfv4.txt', 'type': 'text'},
    {'url': 'https://raw.githubusercontent.com/ZhiXuanWang/cf-speed-dns/refs/heads/main/ipTop10.html', 'type': 'text'},
    {'url': 'https://raw.githubusercontent.com/yonggekkk/Cloudflare_vless_trojan/refs/heads/main/CF%E4%BC%98%E9%80%89%E5%8F%8D%E4%BB%A3IP(%E7%94%B5%E8%84%91%E7%89%88).zip', 'type': 'zip'}
]

# 正则表达式用于匹配IP地址
ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'

# 设置请求头
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0 Safari/537.36'
}

# 如果ip.txt存在，则删除它
if os.path.exists('ip.txt'):
    os.remove('ip.txt')

# 使用 set 去重存储IP
ip_set = set()

def extract_ips_from_text(text):
    return re.findall(ip_pattern, text)

def process_html(content):
    soup = BeautifulSoup(content, 'html.parser')
    elements = soup.find_all('tr')  # 只在HTML页面中查找<tr>
    for element in elements:
        text = element.get_text()
        ips = extract_ips_from_text(text)
        ip_set.update(ips)

def detect_encoding(byte_content):
    result = chardet.detect(byte_content)
    return result['encoding']

def process_zip(url):
    try:
        print(f"正在抓取和解压 ZIP 文件: {url}")
        response = requests.get(url, headers=headers, timeout=30)  # 增加超时时间
        response.raise_for_status()

        with zipfile.ZipFile(BytesIO(response.content)) as z:
            for filename in z.namelist():
                with z.open(filename) as file:
                    byte_content = file.read()
                    encoding = detect_encoding(byte_content)
                    if encoding is None:
                        encoding = 'utf-8'  # 默认使用 utf-8 编码
                    content = byte_content.decode(encoding, errors='ignore')
                    ips = extract_ips_from_text(content)
                    ip_set.update(ips)

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {url}，错误: {e}")
    except Exception as e:
        print(f"处理 ZIP 文件时出错: {url}，错误: {e}")

for info in url_info:
    url = info['url']
    content_type = info['type']

    try:
        print(f"正在抓取: {url}")
        response = requests.get(url, headers=headers, timeout=30)  # 增加超时时间
        response.raise_for_status()

        if content_type == 'html':
            process_html(response.text)
        elif content_type == 'text':
            ips = extract_ips_from_text(response.text)
            ip_set.update(ips)
        elif content_type == 'zip':
            process_zip(url)

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {url}，错误: {e}")
    except Exception as e:
        print(f"处理 URL 时出错: {url}，错误: {e}")

# 将去重后的IP写入文件
with open('ip.txt', 'w', encoding='utf-8') as f:
    for ip in sorted(ip_set):
        f.write(ip + '\n')

print(f"共提取到 {len(ip_set)} 个唯一IP，已保存至 ip.txt")



