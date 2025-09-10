#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Broker XML Parser
解析broker.xml文件，提取brokerid和MarketData地址，输出JSON格式
"""

import xml.etree.ElementTree as ET
import json
import sys
import os

def parse_broker_xml(xml_file_path):
    """
    解析broker.xml文件，提取brokerid和MarketData地址
    
    Args:
        xml_file_path (str): XML文件路径
        
    Returns:
        list: 包含broker信息的列表
    """
    try:
        # 解析XML文件，处理GB2312编码
        with open(xml_file_path, 'r', encoding='gb2312') as f:
            content = f.read()
        root = ET.fromstring(content)
        
        brokers = []
        
        # 遍历所有broker节点
        for broker in root.findall('broker'):
            broker_info = {
                'brokerid': broker.get('BrokerID'),
                'broker_name': broker.get('BrokerName'),
                'broker_ename': broker.get('BrokerEName'),
                'servers': []
            }
            
            # 遍历所有服务器
            servers = broker.find('Servers')
            if servers is not None:
                for server in servers.findall('Server'):
                    server_info = {
                        'name': server.find('Name').text if server.find('Name') is not None else '',
                        'market_data': []
                    }
                    
                    # 提取MarketData地址
                    market_data = server.find('MarketData')
                    if market_data is not None:
                        for item in market_data.findall('item'):
                            if item.text:
                                server_info['market_data'].append(item.text.strip())
                    
                    broker_info['servers'].append(server_info)
            
            brokers.append(broker_info)
        
        return brokers
        
    except ET.ParseError as e:
        print(f"XML解析错误: {e}")
        return []
    except FileNotFoundError:
        print(f"文件未找到: {xml_file_path}")
        return []
    except Exception as e:
        print(f"解析过程中发生错误: {e}")
        return []

def main():
    """主函数"""
    # XML文件路径
    xml_file_path = r"c:\Users\Mayn\AppData\Roaming\Q72_shinny_21990_standard\20250821104928\broker.xml"
    
    # 检查文件是否存在
    if not os.path.exists(xml_file_path):
        print(f"错误: 文件不存在 - {xml_file_path}")
        return
    
    # 解析XML文件
    print("正在解析broker.xml文件...")
    brokers = parse_broker_xml(xml_file_path)
    
    if not brokers:
        print("未找到任何broker信息")
        return
    
    # 输出结果
    print(f"找到 {len(brokers)} 个broker")
    print("\n解析结果:")
    print("=" * 50)
    
    # 输出JSON格式
    result_json = json.dumps(brokers, ensure_ascii=False, indent=2)
    print(result_json)
    
    # 保存到文件
    output_file = "broker_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(result_json)
    
    print(f"\n结果已保存到: {output_file}")
    
    # 显示简要统计信息
    print("\n统计信息:")
    print("-" * 30)
    for broker in brokers:
        total_market_data = sum(len(server['market_data']) for server in broker['servers'])
        print(f"BrokerID: {broker['brokerid']}, 名称: {broker['broker_name']}, MarketData地址数量: {total_market_data}")

if __name__ == "__main__":
    main()
