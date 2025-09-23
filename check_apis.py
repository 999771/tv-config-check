import json
import requests
import base58
import time
import os
from glob import glob  # 用于查找多个JSON文件

def is_api_working(url, timeout=15, max_retries=3):
    """
    检查API是否可用，增加超时时间和重试机制
    :param url: 要检查的API地址
    :param timeout: 每次请求超时时间（秒）
    :param max_retries: 最大重试次数
    :return: 布尔值，API是否可用
    """
    for attempt in range(max_retries):
        try:
            # 先尝试HEAD请求（轻量）
            response = requests.head(
                url, 
                timeout=timeout, 
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"}  # 模拟浏览器请求
            )
            if 200 <= response.status_code < 400:
                return True
        except:
            try:
                # HEAD失败尝试GET请求
                response = requests.get(
                    url, 
                    timeout=timeout, 
                    allow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0"},
                    stream=True  # 不下载完整内容，只获取响应头
                )
                if 200 <= response.status_code < 400:
                    return True
            except Exception as e:
                print(f"第{attempt+1}次尝试失败: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # 重试间隔
    return False

def process_json_file(input_path, output_dir):
    """处理单个JSON文件"""
    # 读取原始配置
    with open(input_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 提取文件名（用于输出）
    filename = os.path.basename(input_path)
    print(f"\n开始处理文件: {filename}")
    
    # 检查API站点
    valid_sites = {}
    api_sites = config.get('api_site', {})
    print(f"发现 {len(api_sites)} 个API站点，开始检查...")
    
    for site_key, site_info in api_sites.items():
        api_url = site_info.get('api')
        site_name = site_info.get('name', site_key)
        print(f"检查 {site_name} ({api_url})...")
        
        if is_api_working(api_url):
            valid_sites[site_key] = site_info
            print(f"✅ {site_name} 可用")
        else:
            print(f"❌ {site_name} 多次尝试失败，将被移除")
        
        time.sleep(1)  # 避免请求过于频繁
    
    # 创建新配置
    new_config = {
        "cache_time": config.get('cache_time', 7200),
        "api_site": valid_sites
    }
    
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
