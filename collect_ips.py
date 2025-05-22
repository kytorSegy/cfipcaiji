import requests
import re
import os
from bs4 import BeautifulSoup

# 目标URL列表
urls = [
    'https://ip.164746.xyz',
    'https://raw.githubusercontent.com/ymyuuu/IPDB/refs/heads/main/BestCF/bestcfv4.txt',
    'https://raw.githubusercontent.com/ZhiXuanWang/cf-speed-dns/refs/heads/main/ipTop10.html'，
    'https://raw.githubusercontent.com/ymyuuu/IPDB/refs/heads/main/BestProxy/bestproxy%26country.txt',
    'https://raw.githubusercontent.com/ymyuuu/IPDB/refs/heads/main/BestGC/bestgcv4.txt'
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

def get_ip_location(ip):
    try:
        response = requests.get(f'https://ipinfo.io/{ip}/json', timeout=10)
        response.raise_for_status()
        data = response.json()
        location = data.get('region', 'Unknown') + ', ' + data.get('country', 'Unknown')
        return location
    except requests.exceptions.RequestException as e:
        print(f"无法获取 {ip} 的位置信息，错误: {e}")
        return 'Unknown'

for url in urls:
    try:
        print(f"正在抓取: {url}")
        response = requests.get(url, headers=headers, timeout=30)  # 增加超时时间
        response.raise_for_status()

        if 'text/html' in response.headers['Content-Type']:
            process_html(response.text)
        else:
            ips = extract_ips_from_text(response.text)
            ip_set.update(ips)

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {url}，错误: {e}")
    except Exception as e:
        print(f"处理 URL 时出错: {url}，错误: {e}")

# 获取每个IP的位置信息并写入文件
with open('ip.txt', 'w', encoding='utf-8') as f:
    for ip in sorted(ip_set):
        location = get_ip_location(ip)
        f.write(f"{ip} ({location})\n")

print(f"共提取到 {len(ip_set)} 个唯一IP及其所属地区，已保存至 ip.txt")



