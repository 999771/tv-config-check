import json
import requests
import base58
import time
import os
import random
from glob import glob
from urllib.parse import urlparse

def is_api_working(url, timeout=30, max_retries=5):
    """
    检测API是否可用，使用更真实的请求头避免403错误
    """
    # 解析URL获取域名用于Referer
    parsed_url = urlparse(url)
    domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    # 更真实的浏览器请求头
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": domain,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }

    # 备用User-Agent列表
    backup_user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
    ]

    for attempt in range(max_retries):
        try:
            # 随机选择User-Agent
            headers["User-Agent"] = random.choice(backup_user_agents)
            
            # 发送GET请求
            response = requests.get(
                url, 
                timeout=timeout, 
                allow_redirects=True,
                headers=headers,
                verify=True
            )
            
            # 检查响应状态码
            if response.status_code == 200:
                # 尝试解析JSON响应
                try:
                    data = response.json()
                    # 检查返回的数据结构是否合理
                    if isinstance(data, dict) and 'list' in data or 'data' in data or 'vod' in str(data).lower():
                        return True
                    elif isinstance(data, list):
                        return True
                    else:
                        print(f"⚠️ API返回数据结构异常")
                        continue
                except:
                    # 检查是否为HTML页面（可能是错误的API）
                    if '<html' in response.text[:100].lower() or '<!doctype' in response.text[:100].lower():
                        print(f"⚠️ 返回的是HTML页面，可能不是有效的API")
                        continue
                    # 即使不是JSON，200状态码也表示服务器响应正常
                    return True
            elif response.status_code == 403:
                print(f"⚠️ 第{attempt+1}次尝试返回403，更换User-Agent重试...")
                continue
            elif response.status_code == 404:
                print(f"⚠️ API不存在 (404): {url}")
                return False
            else:
                print(f"⚠️ 状态码异常: {response.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt + random.uniform(0.5, 1.5))
                continue

        except requests.exceptions.Timeout:
            print(f"⚠️ 请求超时 (第{attempt+1}次)")
        except requests.exceptions.ConnectionError:
            print(f"⚠️ 连接错误 (第{attempt+1}次)")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ 请求异常: {str(e)} (第{attempt+1}次)")

        # 重试间隔
        if attempt < max_retries - 1:
            sleep_time = 2 ** attempt + random.uniform(0.5, 1.5)
            print(f"⏳ 等待{sleep_time:.1f}秒后重试...")
            time.sleep(sleep_time)

    return False

def extract_api_sites_from_config(config):
    """从配置文件中提取所有API站点信息"""
    api_sites = []
    
    def find_api_sites(obj, path=""):
        if isinstance(obj, dict):
            # 检查是否是api_site结构
            if 'api' in obj and 'name' in obj:
                site_id = path.split('.')[-1] if path else "unknown"
                api_sites.append({
                    'id': site_id,
                    'name': obj.get('name', ''),
                    'api': obj.get('api', ''),
                    'detail': obj.get('detail', '') or obj.get('detailUrl', '')
                })
            else:
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    find_api_sites(value, new_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                find_api_sites(item, f"{path}[{i}]")
    
    # 特别处理api_site字段
    if 'api_site' in config and isinstance(config['api_site'], dict):
        for site_id, site_info in config['api_site'].items():
            if isinstance(site_info, dict) and 'api' in site_info:
                api_sites.append({
                    'id': site_id,
                    'name': site_info.get('name', ''),
                    'api': site_info.get('api', ''),
                    'detail': site_info.get('detail', '') or site_info.get('detailUrl', '')
                })
    else:
        # 如果没有api_site字段，尝试在整个配置中查找
        find_api_sites(config)
    
    return api_sites

def process_config_file(input_path, output_dir):
    """处理配置文件"""
    with open(input_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    filename = os.path.basename(input_path)
    print(f"\n开始处理文件: {filename}")
    
    # 提取API站点信息
    api_sites = extract_api_sites_from_config(config)
    print(f"发现 {len(api_sites)} 个API站点")
    
    if not api_sites:
        print(f"⚠️ 未找到API站点信息")
        return
    
    # 检测可用的API
    valid_api_sites = []
    for site in api_sites:
        print(f"检查API: {site['api']} ({site['name']})")
        if is_api_working(site['api']):
            valid_api_sites.append(site)
            print(f"✅ 可用")
        else:
            print(f"❌ 不可用，已排除")
    
    print(f"检测完成，可用API数量: {len(valid_api_sites)}")
    
    # 生成ouonnkiTV格式的列表文件
    base_name = os.path.splitext(filename)[0]
    if base_name.endswith('-config'):
        ouonnki_name = base_name.replace('-config', '-ouonnkiTV.json')
    else:
        ouonnki_name = f"{base_name}-ouonnkiTV.json"
    
    ouonnki_path = os.path.join(output_dir, ouonnki_name)
    
    # 创建ouonnkiTV格式的列表
    ouonnki_list = []
    for site in valid_api_sites:
        ouonnki_list.append({
            "id": site['id'],
            "name": site['name'],
            "url": site['api'],
            "detailUrl": site['detail'],
            "isEnabled": True
        })
    
    # 写入ouonnkiTV格式文件
    with open(ouonnki_path, 'w', encoding='utf-8') as f:
        json.dump(ouonnki_list, f, ensure_ascii=False, indent=4)
    
    print(f"已生成ouonnkiTV格式文件: {ouonnki_path}")
    
    # 生成过滤后的原格式配置文件（保留原文件名）
    if 'api_site' in config and isinstance(config['api_site'], dict):
        # 只保留可用的api_site
        filtered_api_site = {}
        for site in valid_api_sites:
            if site['id'] in config['api_site']:
                filtered_api_site[site['id']] = config['api_site'][site['id']]
        
        filtered_config = config.copy()
        filtered_config['api_site'] = filtered_api_site
        
        # 使用原文件名保存过滤后的配置文件
        filtered_path = os.path.join(output_dir, filename)
        
        with open(filtered_path, 'w', encoding='utf-8') as f:
            json.dump(filtered_config, f, ensure_ascii=False, indent=4)
        
        print(f"已生成过滤后的原格式文件: {filtered_path}")
        
        # 仅对检测后的json文件使用base58编码处理
        base58_filename = f"{os.path.splitext(filename)[0]}_base58.txt"
        base58_path = os.path.join(output_dir, base58_filename)
        
        with open(filtered_path, 'rb') as f:
            base58_encoded = base58.b58encode(f.read()).decode('utf-8')
        
        with open(base58_path, 'w', encoding='utf-8') as f:
            f.write(base58_encoded)
        
        print(f"已生成base58编码: {base58_path}")

def main():
    input_dir = 'Initial'
    output_dir = 'output'
    
    # 检查输入目录是否存在
    if not os.path.exists(input_dir):
        print(f"错误: 输入目录 '{input_dir}' 不存在")
        return
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有-config.json文件
    config_files = glob(os.path.join(input_dir, '*-config.json'))
    # 也包括sub-config.json
    sub_config = os.path.join(input_dir, 'sub-config.json')
    if os.path.exists(sub_config):
        config_files.append(sub_config)
    
    # 去重，避免重复处理
    config_files = list(set(config_files))
    
    if not config_files:
        print(f"警告: {input_dir} 中未找到 *-config.json 或 sub-config.json 文件")
        return
    
    print(f"发现 {len(config_files)} 个配置文件，开始处理...")
    for config_file in config_files:
        try:
            process_config_file(config_file, output_dir)
        except Exception as e:
            print(f"处理文件 {config_file} 时出错: {str(e)}")
            continue
    
    print("\n所有文件处理完成!")

if __name__ == "__main__":
    # 禁用SSL警告
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    main()
