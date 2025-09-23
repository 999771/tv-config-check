import json
import requests
import base58
import time

def is_api_working(url, timeout=10):
    """检查API是否可以正常访问"""
    try:
        # 发送HEAD请求检查连通性（比GET更轻量）
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        # 200-399之间的状态码视为有效
        return 200 <= response.status_code < 400
    except:
        try:
            # 如果HEAD请求失败，尝试GET请求
            response = requests.get(url, timeout=timeout, allow_redirects=True)
            return 200 <= response.status_code < 400
        except:
            return False

def main():
    # 读取原始配置文件
    with open('sub-config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 保存原始缓存时间
    cache_time = config.get('cache_time', 7200)
    
    # 检查每个API站点
    valid_sites = {}
    api_sites = config.get('api_site', {})
    
    print(f"开始检查 {len(api_sites)} 个API站点...")
    
    for site_key, site_info in api_sites.items():
        api_url = site_info.get('api')
        print(f"检查 {site_info.get('name')} ({api_url})...")
        
        if is_api_working(api_url):
            valid_sites[site_key] = site_info
            print(f"✅ {site_info.get('name')} 可用")
        else:
            print(f"❌ {site_info.get('name')} 不可用，将被移除")
        
        # 避免请求过于频繁
        time.sleep(1)
    
    # 创建新的配置
    new_config = {
        "cache_time": cache_time,
        "api_site": valid_sites
    }
    
    # 保存新的配置文件
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(new_config, f, ensure_ascii=False, indent=4)
    
    print(f"\n检查完成，有效站点: {len(valid_sites)} 个")
    print("已生成新的 config.json 文件")
    
    # 生成base58编码
    with open('config.json', 'rb') as f:
        config_bytes = f.read()
    
    base58_encoded = base58.b58encode(config_bytes).decode('utf-8')
    
    with open('config_base58.txt', 'w', encoding='utf-8') as f:
        f.write(base58_encoded)
    
    print("已生成base58编码文件 config_base58.txt")

if __name__ == "__main__":
    main()
