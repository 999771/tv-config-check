import json
import requests
import base58
import time
import os  # 用于创建output文件夹

def is_api_working(url, timeout=10):
    """检查API是否可以正常访问"""
    try:
        # 发送HEAD请求检查连通性
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return 200 <= response.status_code < 400
    except:
        try:
            # HEAD失败尝试GET
            response = requests.get(url, timeout=timeout, allow_redirects=True)
            return 200 <= response.status_code < 400
        except:
            return False

def main():
    # 关键修复：从Initial文件夹读取sub-config.json
    with open('Initial/sub-config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    cache_time = config.get('cache_time', 7200)
    api_sites = config.get('api_site', {})
    
    print(f"开始检查 {len(api_sites)} 个API站点...")
    
    valid_sites = {}
    for site_key, site_info in api_sites.items():
        api_url = site_info.get('api')
        print(f"检查 {site_info.get('name')} ({api_url})...")
        
        if is_api_working(api_url):
            valid_sites[site_key] = site_info
            print(f"✅ {site_info.get('name')} 可用")
        else:
            print(f"❌ {site_info.get('name')} 不可用，将被移除")
        
        time.sleep(1)  # 避免请求过于频繁
    
    # 创建output文件夹（如果不存在）
    os.makedirs('output', exist_ok=True)
    
    # 保存新的config.json到output文件夹
    new_config = {
        "cache_time": cache_time,
        "api_site": valid_sites
    }
    with open('output/config.json', 'w', encoding='utf-8') as f:
        json.dump(new_config, f, ensure_ascii=False, indent=4)
    
    print(f"\n检查完成，有效站点: {len(valid_sites)} 个")
    print("已生成 output/config.json 文件")
    
    # 生成base58编码并保存到output文件夹
    with open('output/config.json', 'rb') as f:
        config_bytes = f.read()
    base58_encoded = base58.b58encode(config_bytes).decode('utf-8')
    
    with open('output/config_base58.txt', 'w', encoding='utf-8') as f:
        f.write(base58_encoded)
    
    print("已生成 output/config_base58.txt 文件")

if __name__ == "__main__":
    main()
