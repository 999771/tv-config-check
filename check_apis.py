import json
import requests
import base58
import time
import os
from glob import glob

def is_api_working(url, timeout=25, max_retries=4):
    """
    增强版API检测：解决403访问限制问题
    增加更多浏览器模拟头信息，优化重试策略
    """
    # 超级模拟浏览器请求头（解决403核心）
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",  # 模拟从谷歌跳转
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        # 模拟常见Cookie（部分网站需要基础Cookie才能访问）
        "Cookie": "Hm_lvt_123=123456; __cf_bm=abcdefg; _ga=GA1.2.123456789"
    }

    for attempt in range(max_retries):
        try:
            # 第一次尝试：带完整头信息的GET请求（直接模拟浏览器行为）
            response = requests.get(
                url, 
                timeout=timeout, 
                allow_redirects=True,
                headers=headers,
                verify=False,  # 跳过SSL验证
                stream=True  # 不下载内容，只获取响应头
            )
            
            # 特殊处理403状态码：尝试更换User-Agent再试
            if response.status_code == 403:
                print("⚠️ 服务器返回403，尝试更换浏览器标识...")
                headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15"
                continue  # 进入下一次重试
            
            # 200-399之间的状态码视为有效
            if 200 <= response.status_code < 400:
                return True
            else:
                print(f"⚠️ 状态码异常: {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"⚠️ 第{attempt+1}次请求失败: {str(e)}")

        # 重试间隔递增（1s→2s→4s→8s）
        if attempt < max_retries - 1:
            sleep_time = 2 **attempt
            print(f"⏳ 等待{sleep_time}秒后重试...")
            time.sleep(sleep_time)

    return False

def extract_api_sites(config):
    """
    从任意JSON结构中提取API站点信息
    支持字典、列表等多种结构
    """
    api_sites = {}
    
    # 情况1：如果是列表结构（你的ouonnkiTV.json属于这种情况）
    if isinstance(config, list):
        print(f"🔍 检测到列表结构，尝试从中提取API信息...")
        for idx, item in enumerate(config):
            if isinstance(item, dict):
                # 提取包含url和name的条目（适配你的JSON结构）
                if "url" in item and "name" in item:
                    site_key = f"site_{idx}"  # 用索引作为键名
                    api_sites[site_key] = {
                        "name": item["name"],
                        "api": item["url"],  # 映射为统一的api字段
                        "id": item.get("id", site_key),
                        "detailUrl": item.get("detailUrl", ""),
                        "isEnabled": item.get("isEnabled", True)
                    }
    
    # 情况2：如果是字典结构，且包含api_site字段
    elif isinstance(config, dict):
        if "api_site" in config and isinstance(config["api_site"], dict):
            api_sites = config["api_site"]
        # 情况3：如果是字典结构，但直接包含API信息（如单独的API对象）
        elif "url" in config and "name" in config:
            api_sites["single_site"] = {
                "name": config["name"],
                "api": config["url"],
                "id": config.get("id", "single_site"),
                "detailUrl": config.get("detailUrl", ""),
                "isEnabled": config.get("isEnabled", True)
            }
    
    return api_sites

def process_json_file(input_path, output_dir):
    """处理单个JSON文件，支持列表和字典结构"""
    # 读取文件
    with open(input_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    filename = os.path.basename(input_path)
    print(f"\n开始处理文件: {filename}")
    
    # 提取API站点（核心修复：支持列表结构）
    api_sites = extract_api_sites(config)
    
    if not api_sites:
        print(f"⚠️ 未从 {filename} 中找到任何API站点信息")
    else:
        print(f"发现 {len(api_sites)} 个API站点，开始检查...")
    
    # 检查并筛选可用站点
    valid_sites = {}
    for site_key, site_info in api_sites.items():
        api_url = site_info.get('api', '')
        site_name = site_info.get('name', site_key)
        
        # 只检测包含vod或json的API
        if "vod" not in api_url.lower() and "json" not in api_url.lower():
            print(f"ℹ️ {site_name} ({api_url}) 不包含vod/json，直接保留")
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
    # 根据原始结构类型，插入有效站点
    if isinstance(config, list):
        # 对于列表结构，重建列表只保留有效站点
        new_config = []
        valid_ids = {site["id"] for site in valid_sites.values()}
        for item in config:
            if isinstance(item, dict) and item.get("id") in valid_ids:
                new_config.append(item)
    elif isinstance(config, dict):
        # 对于字典结构，替换api_site字段
        new_config["api_site"] = valid_sites
    
    # 保存结果
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(new_config, f, ensure_ascii=False, indent=4)
    
    # 生成base58编码
    base58_filename = f"{os.path.splitext(filename)[0]}_base58.txt"
    with open(output_path, 'rb') as f:
        base58_encoded = base58.b58encode(f.read()).decode('utf-8')
    with open(os.path.join(output_dir, base58_filename), 'w', encoding='utf-8') as f:
        f.write(base58_encoded)
    
    print(f"已保存处理结果到: {output_path}")

def main():
    input_dir = 'Initial'
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    
    json_files = glob(os.path.join(input_dir, '*.json'))
    if not json_files:
        print(f"警告: {input_dir} 文件夹中未找到JSON文件")
        return
    
    print(f"发现 {len(json_files)} 个JSON文件，开始处理...")
    for json_file in json_files:
        process_json_file(json_file, output_dir)
    
    print("\n所有文件处理完成!")

if __name__ == "__main__":
    # 禁用SSL警告
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    main()
