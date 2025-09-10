#!/usr/bin/env python3
"""
CTP市场数据回调调试工具
通过多种方式检测数据流问题
"""

import subprocess
import time
import threading
import os
import sys

def check_process_activity():
    """检查market_data_server进程活动"""
    print("\n🔍 检查进程活动...")
    try:
        # 获取进程PID
        result = subprocess.run(['pgrep', '-f', 'market_data_server'], 
                              capture_output=True, text=True)
        pids = result.stdout.strip().split('\n')
        
        if not pids or pids == ['']:
            print("❌ market_data_server进程未找到")
            return []
            
        for pid in pids:
            if pid:
                print(f"📊 进程PID: {pid}")
                
                # 检查进程状态
                try:
                    with open(f'/proc/{pid}/stat', 'r') as f:
                        stat = f.read().split()
                        state = stat[2]  # 进程状态
                        print(f"   状态: {state}")
                        
                    # 检查进程打开的文件描述符
                    fd_count = len(os.listdir(f'/proc/{pid}/fd/'))
                    print(f"   文件描述符: {fd_count}")
                    
                    # 检查网络连接
                    net_result = subprocess.run(['netstat', '-p'], 
                                              capture_output=True, text=True)
                    ctp_connections = [line for line in net_result.stdout.split('\n') 
                                     if pid in line and ('ESTABLISHED' in line or 'LISTEN' in line)]
                    print(f"   网络连接数: {len(ctp_connections)}")
                    
                except Exception as e:
                    print(f"   ⚠️ 无法读取进程详情: {e}")
                    
        return pids
    except Exception as e:
        print(f"❌ 检查进程失败: {e}")
        return []

def monitor_ctp_flow_files():
    """监控CTP流文件变化"""
    print("\n🔍 监控CTP流文件变化...")
    
    initial_files = {}
    ctpflow_dir = 'ctpflow'
    
    if not os.path.exists(ctpflow_dir):
        print(f"❌ CTP流目录不存在: {ctpflow_dir}")
        return
        
    # 记录初始文件状态
    for root, dirs, files in os.walk(ctpflow_dir):
        for file in files:
            if file.endswith('.con'):
                filepath = os.path.join(root, file)
                try:
                    stat = os.stat(filepath)
                    initial_files[filepath] = {
                        'size': stat.st_size,
                        'mtime': stat.st_mtime
                    }
                except:
                    pass
    
    print(f"📊 找到 {len(initial_files)} 个.con文件")
    
    # 监控30秒
    print("📡 开始监控30秒...")
    start_time = time.time()
    changes_detected = 0
    
    while time.time() - start_time < 30:
        time.sleep(2)
        
        current_files = {}
        for root, dirs, files in os.walk(ctpflow_dir):
            for file in files:
                if file.endswith('.con'):
                    filepath = os.path.join(root, file)
                    try:
                        stat = os.stat(filepath)
                        current_files[filepath] = {
                            'size': stat.st_size,
                            'mtime': stat.st_mtime
                        }
                    except:
                        pass
        
        # 检查变化
        for filepath, current_stat in current_files.items():
            if filepath in initial_files:
                initial_stat = initial_files[filepath]
                if (current_stat['size'] != initial_stat['size'] or 
                    current_stat['mtime'] != initial_stat['mtime']):
                    
                    broker_name = filepath.split('/')[-2]  # 获取broker名称
                    file_name = filepath.split('/')[-1]
                    print(f"📝 文件变化: {broker_name}/{file_name} "
                          f"(大小: {initial_stat['size']}→{current_stat['size']})")
                    changes_detected += 1
            else:
                # 新文件
                broker_name = filepath.split('/')[-2]
                file_name = filepath.split('/')[-1]
                print(f"🆕 新文件: {broker_name}/{file_name}")
                changes_detected += 1
        
        initial_files = current_files
        elapsed = int(time.time() - start_time)
        print(f"⏱️ 监控中... {elapsed}s/30s (检测到{changes_detected}个变化)")
    
    print(f"✅ 监控完成，共检测到 {changes_detected} 个文件变化")
    return changes_detected

def test_redis_write_manually():
    """手动测试Redis写入功能"""
    print("\n🧪 手动测试Redis写入...")
    try:
        import redis
        r = redis.Redis(host='192.168.2.27', port=6379, decode_responses=True)
        
        # 测试写入
        test_key = "test_market_data:rb2505"
        test_data = '{"instrument_id":"rb2505","last_price":4000.0,"test":true}'
        
        result = r.set(test_key, test_data)
        if result:
            print("✅ Redis写入测试成功")
            
            # 验证读取
            read_data = r.get(test_key)
            if read_data == test_data:
                print("✅ Redis读取验证成功")
            else:
                print("❌ Redis读取验证失败")
                
            # 清理测试数据
            r.delete(test_key)
        else:
            print("❌ Redis写入测试失败")
            
    except ImportError:
        print("⚠️ Redis模块未安装")
    except Exception as e:
        print(f"❌ Redis测试失败: {e}")

def check_system_resources():
    """检查系统资源"""
    print("\n🔍 检查系统资源...")
    try:
        # 内存使用
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
            for line in meminfo.split('\n'):
                if 'MemAvailable:' in line:
                    mem_kb = int(line.split()[1])
                    mem_mb = mem_kb // 1024
                    print(f"💾 可用内存: {mem_mb} MB")
                    break
        
        # CPU负载
        with open('/proc/loadavg', 'r') as f:
            loadavg = f.read().strip().split()
            print(f"⚡ CPU负载: {loadavg[0]} (1分钟)")
            
        # 磁盘空间
        result = subprocess.run(['df', '-h', '.'], capture_output=True, text=True)
        for line in result.stdout.split('\n')[1:]:
            if line.strip():
                parts = line.split()
                if len(parts) >= 4:
                    print(f"💾 磁盘空间: 已用{parts[2]}/总计{parts[1]} ({parts[4]})")
                    break
                    
    except Exception as e:
        print(f"❌ 系统资源检查失败: {e}")

def main():
    print("🔍 CTP市场数据回调调试工具")
    print("=" * 50)
    
    # 1. 检查进程活动
    pids = check_process_activity()
    
    # 2. 检查系统资源
    check_system_resources()
    
    # 3. 测试Redis写入
    test_redis_write_manually()
    
    # 4. 监控CTP流文件变化
    changes = monitor_ctp_flow_files()
    
    # 5. 总结
    print("\n📋 诊断总结")
    print("=" * 30)
    
    if not pids:
        print("❌ 关键问题: market_data_server进程未运行")
    elif changes == 0:
        print("❌ 关键问题: CTP流文件无变化，可能连接有问题")
        print("   建议: 检查CTP服务器地址和登录凭据")
    else:
        print(f"✅ CTP连接活跃: {changes}个文件变化")
        print("❓ 可能问题: CTP连接正常但市场数据回调未触发")
        print("   建议: 检查OnRtnDepthMarketData回调实现")
    
    print("\n💡 进一步调试建议:")
    print("1. 检查当前是否为交易时间")
    print("2. 验证订阅的合约代码是否正确")
    print("3. 查看服务器输出日志")
    print("4. 确认CTP账号是否有行情权限")

if __name__ == "__main__":
    main()