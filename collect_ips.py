import urllib.request
import urllib.error
import re
import os
import socket
import json

# =============================================================================
# 脚本功能概述（无需安装第三方依赖即可运行）：
#   1. 测试本机是否能通过 HTTP GET 访问指定的“ping”网址（https://www.google.com/generate_204）
#   2. 从预设的一组 URL 中抓取内容（使用 urllib），将获取到的 HTML 或纯文本全部当作字符串处理
#   3. 在所有抓取到的内容里使用正则直接匹配并提取出符合 IPv4 格式的 IP 地址
#   4. 对提取到的所有 IP 进行“TCP 端口连通性检测”（示例性检测 80、443、1080 等常见端口）
#   5. 将被判断为“端口有至少一个连通”的 IP 保存到集合里，认为它们是“可能可用节点”
#   6. 对这些“可能可用节点”再使用 urllib 请求 ipinfo.io 的 JSON 接口，获取国家代码，并写入本地文件 ip.txt
#   7. 在控制台打印出各步骤的进度和结果
#
# 使用说明：
#   - 直接在 Python 3 环境下运行本脚本（无需 pip install 任何第三方包），代码只依赖 Python 标准库。
#   - Windows、Linux、macOS 的 Python 3 环境均可直接执行： python check_nodes.py
#   - 输出结果保存在当前目录下的 ip.txt 文件中，每行格式：<IP> (<国家代码>)
#
# 注意事项：
#   - HTTP 请求使用 urllib，若被目标网站屏蔽或重定向可能导致抓取失败。
#   - JSON 解析使用 json 库，若 ipinfo.io 返回异常或网络超时则国家字段显示为 Unknown。
#   - 端口检测使用 socket，一旦网络不通或被防火墙拦截可能误判为“不可用”。
# =============================================================================

# -------------------------------
# 全局变量与配置信息
# -------------------------------

# 目标 URL 列表（无需安装第三方库即可访问）
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

# 匹配 IPv4 地址的正则表达式
IP_PATTERN = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'

# 测试网络连通性的“ping”网址
PING_URL = 'https://www.google.com/generate_204'

# 最终输出文件名
OUTPUT_FILE = 'ip.txt'

# 存储所有提取到的唯一 IP
ip_set = set()

# 存储通过端口连通性检测后认为“可能可用”的 IP
alive_ip_set = set()


# -------------------------------
# 函数：测试本机能否访问指定的 PING_URL
# -------------------------------
def test_connectivity():
    """
    使用 urllib 发起 GET 请求访问 PING_URL，如果返回 HTTP 204，则认为网络连通，否则提示警告。
    """
    print(f"[*] 正在测试本机网络连通性，访问：{PING_URL} …")
    try:
        req = urllib.request.Request(PING_URL, method='GET')
        # 添加一个常见的 User-Agent，模拟浏览器行为
        req.add_header('User-Agent',
                       'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0 Safari/537.36')
        with urllib.request.urlopen(req, timeout=5) as response:
            status = response.getcode()
            if status == 204:
                print("[√] 本机网络连通性正常，能够访问 PING_URL。\n")
            else:
                print(f"[!] 本机访问 PING_URL 返回状态码 {status}，"
                      f"可能网络受限或被拦截，请检查网络环境。\n")
    except Exception as e:
        # 捕获包括超时、DNS 解析失败、连接拒绝等所有异常
        print(f"[×] 测试网络连通性时出现异常：{e}，请检查本地网络或 DNS 配置。\n")


# -------------------------------
# 函数：从字符串中提取所有符合 IPv4 格式的 IP
# -------------------------------
def extract_ips_from_text(text):
    """
    使用正则 IP_PATTERN 在传入的文本 text 中查找所有匹配的 IPv4 地址，
    返回一个列表，可能包含重复项，需要上层调用者自行去重。
    """
    return re.findall(IP_PATTERN, text)


# -------------------------------
# 函数：从指定 URL 抓取内容并提取 IP
# -------------------------------
def fetch_and_extract_ips():
    """
    遍历 URLS 列表，对每个 URL 发起 HTTP GET 请求，将获取到的响应内容
    解码为字符串，然后直接使用正则从整个文本中抽取 IP。
    如果抓取或解码失败，会在控制台打印错误信息并跳过该 URL。
    提取到的 IP 会加入全局 ip_set（自动去重）。
    """
    for url in URLS:
        try:
            print(f"[*] 正在抓取：{url}")
            req = urllib.request.Request(url, method='GET')
            # 设置一个常见的 User-Agent，避免某些站点拒绝访问
            req.add_header('User-Agent',
                           'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/120.0.0 Safari/537.36')
            with urllib.request.urlopen(req, timeout=20) as response:
                # 读取全部响应字节数据
                raw_bytes = response.read()
                # 尝试以 UTF-8 解码，若失败再使用 ISO-8859-1 解码
                try:
                    content = raw_bytes.decode('utf-8', errors='ignore')
                except Exception:
                    content = raw_bytes.decode('iso-8859-1', errors='ignore')

                # 在整个响应文本里用正则抽取所有 IP
                ips = extract_ips_from_text(content)
                if ips:
                    # update 自动去重
                    ip_set.update(ips)

        except Exception as e:
            # 包括 HTTPError、URLError、超时、网络异常等
            print(f"    [!] 请求或解码失败：{url}，原因：{e}")

    print(f"\n[*] 抓取完成，共提取到 {len(ip_set)} 个唯一 IP。\n")


# -------------------------------
# 函数：测试某个 IP:port 是否能建立 TCP 连接
# -------------------------------
def check_port_open(ip, port, timeout=3):
    """
    使用 socket 尝试连接指定 ip:port。
    参数：
      - ip (str)：目标 IP 地址
      - port (int)：目标端口号
      - timeout (int)：超时时间（秒），默认 3 秒
    返回：
      - True：能够建立 TCP 连接
      - False：连接失败（端口未开放或网络不可达）
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        sock.close()
        return True
    except Exception:
        return False


# -------------------------------
# 函数：判断某个 IP 是否“可能可用”
# -------------------------------
def is_node_alive(ip):
    """
    对给定的 IP，依次检测 common_ports 列表中端口是否能连通，只要有一个端口连通就返回 True。
    common_ports 列表包含常见的 HTTP/HTTPS/代理端口，可根据实际需要调整。
    """
    common_ports = [80, 443, 1080]  # 示例：HTTP(80)、HTTPS(443)、SOCKS5(1080)
    for port in common_ports:
        if check_port_open(ip, port):
            return True
    return False


# -------------------------------
# 函数：对提取到的 IP 进行可用性检测，筛选活跃节点
# -------------------------------
def filter_alive_ips():
    """
    遍历全局 ip_set 中的每个 IP，调用 is_node_alive(ip) 进行端口检测，
    如果返回 True，则把该 IP 加入全局 alive_ip_set，并在控制台打印“可用”提示，
    否则打印“不可用”提示。
    """
    print("[*] 开始对提取到的 IP 进行端口连通性检测……")
    for ip in sorted(ip_set):
        if is_node_alive(ip):
            alive_ip_set.add(ip)
            print(f"    [√] 节点可用（端口检测通过）：{ip}")
        else:
            print(f"    [×] 节点不可用（端口检测失败）：{ip}")
    print(f"\n[*] 可用性检测完成，共 {len(alive_ip_set)} 个可能可用 IP。\n")


# -------------------------------
# 函数：查询单个 IP 的国家/地区代码并写入文件
# -------------------------------
def get_ip_location_and_write():
    """
    打开本地 OUTPUT_FILE，以 UTF-8 编码写入：
      - 对 sorted(alive_ip_set) 中的每个 IP，使用 urllib 请求 ipinfo.io JSON 接口
      - 解析返回的 JSON，获取 'country' 字段（若不存在则用 'Unknown'）
      - 将 "<IP> (<国家代码>)" 写入文件，每行一个
    如果写文件或网络请求失败，会在控制台打印异常信息。
    """
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for ip in sorted(alive_ip_set):
                country = 'Unknown'
                try:
                    api_url = f'https://ipinfo.io/{ip}/json'
                    req = urllib.request.Request(api_url, method='GET')
                    req.add_header('User-Agent',
                                   'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                                   'Chrome/120.0.0 Safari/537.36')
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        raw = resp.read().decode('utf-8', errors='ignore')
                        data = json.loads(raw)
                        country = data.get('country', 'Unknown')
                except Exception:
                    # 若任何网络/JSON 解析失败，仍写入 Unknown，不中断整体流程
                    country = 'Unknown'

                # 写入文件，格式：<IP> (<国家代码>)
                f.write(f"{ip} ({country})\n")

        print(f"[*] 可用 IP 及其国家信息已写入文件：{OUTPUT_FILE}\n")
    except Exception as e:
        print(f"[!] 写入文件时发生错误：{e}")


# -------------------------------
# 脚本入口：按顺序调用各个功能
# -------------------------------
if __name__ == '__main__':
    # 1. 先测试本机网络能否访问 PING_URL
    test_connectivity()

    # 2. 抓取所有 URL 并提取 IP
    fetch_and_extract_ips()

    # 3. 对所有提取到的 IP 进行端口连通性检测，筛选活跃节点
    filter_alive_ips()

    # 4. 对“活跃节点”查询地理位置并写入本地文件
    get_ip_location_and_write()

    print("[*] 脚本执行完毕。")
