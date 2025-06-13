import urllib.request
import urllib.error
import re
import os
import socket
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# =============================================================================
# 脚本功能概述（无需安装第三方依赖即可运行）：
#   1. 测试本机是否能通过 HTTP GET 访问指定的“ping”网址（https://www.google.com/generate_204）
#   2. 从预设的一组 URL 中并发抓取内容（使用 urllib），提取 IPv4 地址
#   3. 对提取到的所有 IP 进行“TCP 端口连通性检测”（示例性检测 80、443、1080）
#   4. 对“可能可用节点”获取国家代码，并写入本地文件 ip.txt
#   5. 控制台打印各步骤进度和结果
# =============================================================================

# -------------------------------
# 全局变量与配置信息
# -------------------------------
URLS = [
    'https://ip.164746.xyz',
    'https://raw.githubusercontent.com/ymyuuu/IPDB/refs/heads/main/BestCF/bestcfv4.txt',
    'https://raw.githubusercontent.com/ZhiXuanWang/cf-speed-dns/refs/heads/main/ipTop10.html',
    'https://raw.githubusercontent.com/ymyuuu/IPDB/refs/heads/main/BestProxy/bestproxy%26country.txt',
    'https://raw.githubusercontent.com/ymyuuu/IPDB/refs/heads/main/BestGC/bestgcv4.txt',
    'https://clashfreenode.com/feed/v2ray-20250606.txt',
    'https://raw.githubusercontent.com/asdsadsddas123/freevpn/main/README.md',
    'https://raw.githubusercontent.com/vxiaov/free_proxies/refs/heads/main/links.txt',
    'https://raw.githubusercontent.com/yorkLiu/FreeV2RayNode/refs/heads/main/v2ray.txt',
    'https://raw.githubusercontent.com/mostaghimbot/FreeV2rayConfig/refs/heads/master/subscription_output.txt',
    'https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/filtered/subs/hy2.txt',
    'https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/v2ray/super-sub.txt',
    'https://raw.githubusercontent.com/newbeastly/netproxy/refs/heads/main/ip/local/result.csv'
]

IP_PATTERN = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
PING_URL = 'https://www.google.com/generate_204'
OUTPUT_FILE = 'ip.txt'
MAX_WORKERS = 5
RETRY_LIMIT = 2
common_ports = [80, 443, 1080]
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0 Safari/537.36'
)

ip_set = set()
alive_ip_set = set()
MAX_CHECK_WORKERS = 30


# -------------------------------
# 函数：测试本机能否访问指定的 PING_URL
# -------------------------------
def test_connectivity():
    print(f"[*] 正在测试本机网络连通性，访问：{PING_URL} …")
    try:
        req = urllib.request.Request(PING_URL, headers={'User-Agent': USER_AGENT}, method='GET')
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.getcode() == 204:
                print("[√] 本机网络连通性正常。\n")
            else:
                print(f"[!] 返回状态码 {response.getcode()}，请检查网络环境。\n")
    except Exception as e:
        print(f"[×] 测试失败：{e}，请检查 DNS 或网络设置。\n")


# -------------------------------
# 函数：验证 IP 是否合法
# -------------------------------
def is_valid_ip(ip):
    parts = ip.split('.')
    return len(parts) == 4 and all(0 <= int(part) < 256 for part in parts)


# -------------------------------
# 函数：从字符串中提取所有符合 IPv4 格式的 IP
# -------------------------------
def extract_ips_from_text(text):
    return list(set(ip for ip in re.findall(IP_PATTERN, text) if is_valid_ip(ip)))


# -------------------------------
# 函数：并发抓取单个 URL 的内容
# -------------------------------
def fetch_url(url, retry=0):
    try:
        print(f"[*] 正在抓取：{url}")
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT}, method='GET')
        with urllib.request.urlopen(req, timeout=20) as response:
            raw_bytes = response.read()
            try:
                content = raw_bytes.decode('utf-8', errors='ignore')
            except:
                content = raw_bytes.decode('iso-8859-1', errors='ignore')
            return extract_ips_from_text(content)
    except Exception as e:
        if retry < RETRY_LIMIT:
            print(f"    [!] 请求失败，正在重试第 {retry + 1} 次：{url}")
            return fetch_url(url, retry + 1)
        else:
            print(f"    [!] 请求失败，跳过该地址：{url}")
            return []


# -------------------------------
# 函数：并发抓取所有 URL 并提取 IP
# -------------------------------
def fetch_and_extract_ips():
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(fetch_url, url): url for url in URLS}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                ips = future.result()
                ip_set.update(ips)
            except Exception as exc:
                print(f"    [!] 异常发生在抓取 {url}: {exc}")
    print(f"\n[*] 抓取完成，共提取到 {len(ip_set)} 个唯一 IP。\n")


# -------------------------------
# 函数：测试某个 IP:port 是否能建立 TCP 连接
# -------------------------------
def check_port_open(ip, port, timeout=3):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        sock.close()
        return True
    except:
        return False


# -------------------------------
# 函数：判断某个 IP 是否“可能可用”
# -------------------------------
def is_node_alive(ip):
    with ThreadPoolExecutor(max_workers=3) as executor:  # 保持端口检测并发度
        futures = {executor.submit(check_port_open, ip, port): port for port in common_ports}
        for future in as_completed(futures):
            if future.result():
                return True
    return False


# -------------------------------
# 函数：对提取到的 IP 进行可用性检测
# -------------------------------
def filter_alive_ips():
    print("[*] 开始对提取到的 IP 进行端口连通性检测……")
    alive_ips = []
    with ThreadPoolExecutor(max_workers=MAX_CHECK_WORKERS) as executor:  # 新增并发控制
        future_to_ip = {executor.submit(is_node_alive, ip): ip for ip in ip_set}
        for future in as_completed(future_to_ip):
            ip = future_to_ip[future]
            try:
                if future.result():
                    alive_ips.append(ip)
                    print(f"    [√] 节点可用：{ip}")
                else:
                    print(f"    [×] 节点不可用：{ip}")
            except Exception as exc:
                print(f"    [!] 异常发生在检测 {ip}: {exc}")
    alive_ip_set.update(alive_ips)
    print(f"\n[*] 可用性检测完成，共 {len(alive_ip_set)} 个可能可用 IP。\n")


# -------------------------------
# 函数：查询 IP 地理位置并写入文件
# -------------------------------
def get_ip_location_and_write():
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for ip in sorted(alive_ip_set):
                country = 'Unknown'
                try:
                    api_url = f'https://ipinfo.io/{ip}/json'
                    req = urllib.request.Request(api_url, headers={'User-Agent': USER_AGENT}, method='GET')
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        data = json.loads(resp.read().decode('utf-8', errors='ignore'))
                        country = data.get('country', 'Unknown')
                except:
                    pass
                f.write(f"{ip} ({country})\n")
        print(f"[*] 可用 IP 已写入文件：{OUTPUT_FILE}\n")
    except Exception as e:
        print(f"[!] 写入文件时出错：{e}")


# -------------------------------
# 主入口函数
# -------------------------------
if __name__ == '__main__':
    test_connectivity()
    fetch_and_extract_ips()
    filter_alive_ips()
    get_ip_location_and_write()
    print("[*] 脚本执行完毕。")
