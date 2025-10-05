import json
import requests
import base58
import time
import os
import random
from glob import glob

def is_api_working(url, timeout=30, max_retries=5):
    """
    检测API是否可用，使用更简单的请求头避免403错误
    """
    # 简化请求头，避免过于复杂的浏览器模拟导致403
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    # 备用User-Agent列表
    backup_user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ]

    for attempt in range(max_retries):
        try:
            # 发送GET请求，不跳过SSL验证
            response = requests.get(
                url, 
                timeout=timeout, 
                allow_redirects=True,
                headers=headers,
                verify=True  # 重新启用SSL验证
            )
            
            # 检查响应状态码
            if response.status_code == 200:
                # 尝试解析JSON响应，确保是有效的API
                try:
                    response.json()
                    return True
                except:
                    # 即使不是JSON，200状态码也表示服务器响应正常
                    return True
            elif response.status_code == 403:
                print(f"⚠️ 第{attempt+1}次尝试返回403，更换User-Agent重试...")
                if attempt < len(backup_user_agents):
                    headers["User-Agent"] = backup_user_agents[attempt]
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

def extract_apis_from_config(config):
    """从配置文件中提取所有API地址"""
    apis = []
    
    def find_apis(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str) and (value.startswith('http') and ('api' in value.lower() or 'vod' in value.lower())):
                    apis.append(value)
                else:
                    find_apis(value)
        elif isinstance(obj, list):
            for item in obj:
                find_apis(item)
    
    find_apis(config)
    # 去重并返回
    return list(set(apis))

def process_config_file(input_path, output_dir):
    """处理配置文件"""
    with open(input_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    filename = os.path.basename(input_path)
    print(f"\n开始处理文件: {filename}")
    
    # 提取API地址
    all_apis = extract_apis_from_config(config)
    print(f"发现 {len(all_apis)} 个API地址")
    
    if not all_apis:
        print(f"⚠️ 未找到API地址")
        return
    
    # 检测可用的API
    valid_apis = []
    for api_url in all_apis:
        print(f"检查API: {api_url}")
        if is_api_working(api_url):
            valid_apis.append(api_url)
            print(f"✅ 可用")
        else:
            print(f"❌ 不可用，已排除")
    
    print(f"检测完成，可用API数量: {len(valid_apis)}")
    
    # 生成ouonnkiTV格式的列表文件
    base_name = os.path.splitext(filename)[0]
    if base_name.endswith('-config'):
        ouonnki_name = base_name.replace('-config', '-ouonnkiTV.json')
    else:
        ouonnki_name = f"{base_name}-ouonnkiTV.json"
    
    ouonnki_path = os.path.join(output_dir, ouonnki_name)
    
    # 创建ouonnkiTV格式的列表
    ouonnki_list = []
    for i, api_url in enumerate(valid_apis):
        site_name = f"站点{i+1}"
        ouonnki_list.append({
            "name": site_name,
            "api": api_url,
            "id": f"site_{i+1}",
            "isEnabled": True
        })
    
    # 写入ouonnkiTV格式文件
    with open(ouonnki_path, 'w', encoding='utf-8') as f:
        json.dump(ouonnki_list, f, ensure_ascii=False, indent=4)
    
    print(f"已生成ouonnkiTV格式文件: {ouonnki_path}")
    
    # 生成base58编码
    base58_filename = f"{os.path.splitext(ouonnki_name)[0]}_base58.txt"
    base58_path = os.path.join(output_dir, base58_filename)
    
    with open(ouonnki_path, 'rb') as f:
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
