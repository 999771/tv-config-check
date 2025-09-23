import json
import requests
import base58
import time
import os
from glob import glob  # 用于查找多个JSON文件

def is_api_working(url, timeout=20, max_retries=3):
    """
    检查API是否可用，增强版检测逻辑
    :param url: 要检查的API地址
    :param timeout: 每次请求超时时间（秒）
    :param max_retries: 最大重试次数
    :return: 布尔值，API是否可用
    """
    # 增强请求头，模拟真实浏览器行为
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    }

    for attempt in range(max_retries):
        try:
            # 第一次尝试：HEAD请求（轻量检测）
            response = requests.head(
                url, 
                timeout=timeout, 
                allow_redirects=True,
                headers=headers,
                verify=False  # 跳过SSL证书验证（解决部分证书问题）
            )
            if 200 <= response.status_code < 400:
                return True

        except requests.exceptions.SSLError:
            print(f"⚠️ SSL证书验证失败，尝试跳过验证...")
        except Exception as e:
            print(f"⚠️ 第{attempt+1}次HEAD请求失败: {str(e)}")

        # HEAD失败后尝试GET请求（获取头部信息，不下载内容）
        try:
            response = requests.get(
                url, 
                timeout=timeout, 
                allow_redirects=True,
                headers=headers,
                stream=True,  # 不下载完整内容
                verify=False  # 跳过SSL证书验证
            )
            # 只需要确认响应状态码有效，不需要读取内容
            if 200 <= response.status_code < 400:
                return True
            else:
                print(f"⚠️ GET请求返回状态码: {response.status_code}")

        except Exception as e:
            print(f"⚠️ 第{attempt+1}次GET请求失败: {str(e)}")

        # 重试间隔递增（避免频繁请求被屏蔽）
        if attempt < max_retries - 1:
            sleep_time = 2 **attempt  # 1s, 2s, 4s...
            print(f"⏳ 等待{sleep_time}秒后重试...")
            time.sleep(sleep_time)

    return False

def process_json_file(input_path, output_dir):
    """处理单个JSON文件"""
    # 读取原始配置
    with open(input_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 修复1：处理JSON结构可能是列表的问题
    if isinstance(config, list):
        print(f"⚠️ 注意：{input_path} 是列表结构，将尝试转换为字典处理")
        # 如果是列表且第一个元素是字典，就用第一个元素
        if len(config) > 0 and isinstance(config[0], dict):
            config = config[0]
        else:
            print(f"❌ {input_path} 格式不符合要求，跳过处理")
            return
    
    # 提取文件名（用于输出）
    filename = os.path.basename(input_path)
    print(f"\n开始处理文件: {filename}")
    
    # 检查API站点
    valid_sites = {}
    # 修复2：确保api_site是字典
    api_sites = config.get('api_site', {})
    if not isinstance(api_sites, dict):
        print(f"⚠️ {filename} 中的api_site不是字典类型，已重置为空")
        api_sites = {}
    
    print(f"发现 {len(api_sites)} 个API站点，开始检查...")
    
    for site_key, site_info in api_sites.items():
        # 确保site_info是字典
        if not isinstance(site_info, dict):
            print(f"⚠️ {site_key} 格式不正确，跳过")
            continue
            
        api_url = site_info.get('api', '')
        site_name = site_info.get('name', site_key)
        
        # 新增：只检测包含"vod"或"json"的API地址
        if "vod" not in api_url and "json" not in api_url:
            print(f"ℹ️ {site_name} ({api_url}) 不包含vod/json，跳过检测")
            valid_sites[site_key] = site_info  # 不检测直接保留
            continue
        
        print(f"\n检查 {site_name} ({api_url})...")
        
        if is_api_working(api_url):
            valid_sites[site_key] = site_info
            print(f"✅ {site_name} 可用")
        else:
            print(f"❌ {site_name} 多次尝试失败，将被移除")
    
    # 创建新配置（保留原始配置中的其他字段）
    new_config = config.copy()  # 复制原始配置
    new_config['api_site'] = valid_sites  # 只替换api_site部分
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存处理后的JSON
    output_path = os.path.join(output_dir, filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(new_config, f, ensure_ascii=False, indent=4)
    
    print(f"已保存处理结果到: {output_path}")
    
    # 生成base58编码
    base58_filename = f"{os.path.splitext(filename)[0]}_base58.txt"
    base58_path = os.path.join(output_dir, base58_filename)
    
    with open(output_path, 'rb') as f:
        config_bytes = f.read()
    
    base58_encoded = base58.b58encode(config_bytes).decode('utf-8')
    with open(base58_path, 'w', encoding='utf-8') as f:
        f.write(base58_encoded)
    
    print(f"已生成base58编码到: {base58_path}")

def main():
    # 配置路径
    input_dir = 'Initial'
    output_dir = 'output'
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取Initial文件夹下所有JSON文件
    json_files = glob(os.path.join(input_dir, '*.json'))
    
    if not json_files:
        print(f"警告: 在 {input_dir} 文件夹中未找到任何JSON文件")
        return
    
    # 处理每个JSON文件
    print(f"发现 {len(json_files)} 个JSON文件，开始批量处理...")
    for json_file in json_files:
        process_json_file(json_file, output_dir)
    
    print("\n所有文件处理完成!")

if __name__ == "__main__":
    main()
