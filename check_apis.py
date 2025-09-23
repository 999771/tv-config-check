import json
import requests
import base58
import time
import os
from glob import glob

def is_api_working(url, timeout=30, max_retries=5):
    """
    精准模拟浏览器请求头，解决403访问问题
    使用用户提供的实际浏览器请求标头
    """
    # 完全复制用户提供的浏览器请求头（解决403的核心）
    headers = {
        "authority": "mozhuazy.com",
        "method": "GET",
        "scheme": "https",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "cache-control": "max-age=0",
        "dnt": "1",
        "priority": "u=0, i",
        "sec-ch-ua": "\"Chromium\";v=\"140\", \"Not=A?Brand\";v=\"24\", \"Microsoft Edge\";v=\"140\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "cross-site",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0"
    }

    # 准备备用User-Agent（用于403重试）
    backup_user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    ]

    for attempt in range(max_retries):
        try:
            # 发送与浏览器完全一致的请求
            response = requests.get(
                url, 
                timeout=timeout, 
                allow_redirects=True,
                headers=headers,
                verify=False,  # 跳过SSL验证
                stream=True
            )
            
            # 处理403状态码：尝试使用备用User-Agent
            if response.status_code == 403:
                print(f"⚠️ 第{attempt+1}次尝试返回403，更换浏览器标识重试...")
                if attempt < len(backup_user_agents):
                    headers["user-agent"] = backup_user_agents[attempt]
                continue
            
            # 200-399之间的状态码视为有效
            if 200 <= response.status_code < 400:
                return True
            else:
                print(f"⚠️ 状态码异常: {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"⚠️ 第{attempt+1}次请求失败: {str(e)}")

        # 智能重试间隔（递增且随机化，避免被识别为机器人）
        if attempt < max_retries - 1:
            sleep_time = 2 **attempt + random.uniform(0.5, 1.5)  # 1.5-2.5s, 2.5-3.5s...
            print(f"⏳ 等待{sleep_time:.1f}秒后重试...")
            time.sleep(sleep_time)

    return False

def extract_api_sites(config):
    """从任意JSON结构提取API站点（支持列表和字典）"""
    api_sites = {}
    
    # 处理列表结构（如ouonnkiTV.json）
    if isinstance(config, list):
        print(f"🔍 检测到列表结构，提取API信息...")
        for idx, item in enumerate(config):
            if isinstance(item, dict):
                # 适配包含url字段的API条目
                if "url" in item:
                    site_key = f"site_{idx}"
                    api_sites[site_key] = {
                        "name": item.get("name", f"站点_{idx}"),
                        "api": item["url"],
                        "id": item.get("id", site_key),
                        "isEnabled": item.get("isEnabled", True)
                    }
    
    # 处理字典结构
    elif isinstance(config, dict):
        # 支持api_site字段
        if "api_site" in config and isinstance(config["api_site"], (dict, list)):
            # 如果api_site是列表，转换为字典处理
            if isinstance(config["api_site"], list):
                for idx, item in enumerate(config["api_site"]):
                    if isinstance(item, dict) and "url" in item:
                        site_key = f"site_{idx}"
                        api_sites[site_key] = {
                            "name": item.get("name", f"站点_{idx}"),
                            "api": item["url"],
                            "id": item.get("id", site_key)
                        }
            else:
                api_sites = config["api_site"]
        # 支持直接包含url的字典
        elif "url" in config:
            api_sites["single_site"] = {
                "name": config.get("name", "默认站点"),
                "api": config["url"],
                "id": config.get("id", "single_site")
            }
    
    return api_sites

def process_json_file(input_path, output_dir):
    """处理单个JSON文件，确保输出覆盖旧文件"""
    # 读取原始文件
    with open(input_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    filename = os.path.basename(input_path)
    print(f"\n开始处理文件: {filename}")
    
    # 提取API站点
    api_sites = extract_api_sites(config)
    
    if not api_sites:
        print(f"⚠️ 未找到API站点信息")
    else:
        print(f"发现 {len(api_sites)} 个API站点，开始检查...")
    
    # 筛选可用站点
    valid_sites = {}
    for site_key, site_info in api_sites.items():
        api_url = site_info.get('api', '')
        site_name = site_info.get('name', site_key)
        
        # 只检测包含vod或json的API
        if "vod" not in api_url.lower() and "json" not in api_url.lower():
            print(f"ℹ️ {site_name} 不包含vod/json，直接保留")
            valid_sites[site_key] = site_info
            continue
        
        print(f"检查 {site_name} ({api_url})...")
        if is_api_working(api_url):
            valid_sites[site_key] = site_info
            print(f"✅ {site_name} 可用")
        else:
            print(f"❌ {site_name} 不可用，已移除")
    
    # 生成新配置（保留原始结构）
    new_config = config
    if isinstance(config, list):
        # 列表结构：只保留有效站点
        valid_ids = {site["id"] for site in valid_sites.values()}
        new_config = [item for item in config if isinstance(item, dict) and item.get("id") in valid_ids]
    elif isinstance(config, dict):
        # 字典结构：更新api_site字段
        new_config["api_site"] = valid_sites
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    
    # 写入文件（直接覆盖旧文件）
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(new_config, f, ensure_ascii=False, indent=4)
    
    # 生成base58编码（同样覆盖旧文件）
    base58_filename = f"{os.path.splitext(filename)[0]}_base58.txt"
    base58_path = os.path.join(output_dir, base58_filename)
    
    with open(output_path, 'rb') as f:
        base58_encoded = base58.b58encode(f.read()).decode('utf-8')
    
    with open(base58_path, 'w', encoding='utf-8') as f:
        f.write(base58_encoded)
    
    print(f"已更新文件: {output_path}")
    print(f"已更新base58编码: {base58_path}")

def main():
    import random  # 延迟导入，仅在主程序运行时使用
    input_dir = 'Initial'
    output_dir = 'output'
    
    # 获取所有JSON文件
    json_files = glob(os.path.join(input_dir, '*.json'))
    if not json_files:
        print(f"警告: {input_dir} 中未找到JSON文件")
        return
    
    print(f"发现 {len(json_files)} 个JSON文件，开始处理...")
    for json_file in json_files:
        process_json_file(json_file, output_dir)
    
    print("\n所有文件处理完成，已自动更新同名文件!")

if __name__ == "__main__":
    # 禁用SSL警告
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    main()
