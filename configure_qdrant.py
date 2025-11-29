#!/usr/bin/env python3
"""
Qdrant 配置助手
帮助用户配置 Qdrant 数据库连接
"""
import os
import sys

def main():
    print("=" * 60)
    print("🔧 Qdrant 数据库配置助手")
    print("=" * 60)
    print()
    
    print("请选择配置方式:")
    print()
    print("1. 使用 Qdrant Cloud（推荐）")
    print("   - 在线服务，无需安装")
    print("   - 访问: https://cloud.qdrant.io/")
    print()
    print("2. 使用本地 Qdrant（需要 Docker）")
    print("   - 完全本地控制")
    print("   - 需要先安装 Docker")
    print()
    
    choice = input("请选择 (1/2): ").strip()
    
    env_file = '.env'
    env_lines = []
    
    # 读取现有的 .env 文件
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_lines = f.readlines()
    else:
        # 从模板创建
        with open('.env.example', 'r') as f:
            env_lines = f.readlines()
    
    if choice == '1':
        # Qdrant Cloud 配置
        print()
        print("=" * 60)
        print("配置 Qdrant Cloud")
        print("=" * 60)
        print()
        print("请按以下步骤操作:")
        print("1. 访问 https://cloud.qdrant.io/ 并注册账号")
        print("2. 创建集群后，在集群详情页面找到:")
        print("   - Cluster URL (例如: https://xxxxx-xxxxx.qdrant.io)")
        print("   - API Key (在 API Keys 标签页创建)")
        print()
        
        qdrant_url = input("请输入 Qdrant URL: ").strip()
        if not qdrant_url:
            print("❌ URL 不能为空")
            return
        
        qdrant_key = input("请输入 API Key: ").strip()
        if not qdrant_key:
            print("❌ API Key 不能为空")
            return
        
        # 更新 .env 文件
        new_lines = []
        for line in env_lines:
            if line.startswith('QDRANT_URL='):
                new_lines.append(f'QDRANT_URL={qdrant_url}\n')
            elif line.startswith('QDRANT_API_KEY='):
                new_lines.append(f'QDRANT_API_KEY={qdrant_key}\n')
            else:
                new_lines.append(line)
        
        with open(env_file, 'w') as f:
            f.writelines(new_lines)
        
        print()
        print("✅ Qdrant Cloud 配置已保存到 .env 文件")
        
    elif choice == '2':
        # 本地 Qdrant 配置
        print()
        print("=" * 60)
        print("配置本地 Qdrant")
        print("=" * 60)
        print()
        
        # 检查 Docker
        import subprocess
        docker_check = subprocess.run(['docker', '--version'], 
                                     capture_output=True, 
                                     text=True)
        if docker_check.returncode != 0:
            print("❌ Docker 未安装")
            print()
            print("请先安装 Docker:")
            print("  macOS: https://docs.docker.com/desktop/install/mac-install/")
            print("  或使用选项 1 的 Qdrant Cloud")
            return
        
        print("✅ Docker 已安装")
        print()
        
        # 检查 Qdrant 容器是否运行
        qdrant_check = subprocess.run(['docker', 'ps', '--filter', 'name=qdrant', '--format', '{{.Names}}'],
                                     capture_output=True, text=True)
        
        if 'qdrant' not in qdrant_check.stdout:
            print("本地 Qdrant 容器未运行")
            start = input("是否现在启动本地 Qdrant 容器? (y/n): ").strip().lower()
            
            if start == 'y':
                print()
                print("正在启动 Qdrant 容器...")
                print("命令: docker run -d -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage --name qdrant qdrant/qdrant")
                print()
                
                os.makedirs('qdrant_storage', exist_ok=True)
                result = subprocess.run([
                    'docker', 'run', '-d',
                    '-p', '6333:6333',
                    '-p', '6334:6334',
                    '-v', f'{os.path.abspath("qdrant_storage")}:/qdrant/storage',
                    '--name', 'qdrant',
                    'qdrant/qdrant'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print("✅ Qdrant 容器已启动")
                else:
                    print(f"❌ 启动失败: {result.stderr}")
                    return
        
        # 更新 .env 文件
        new_lines = []
        for line in env_lines:
            if line.startswith('QDRANT_URL='):
                new_lines.append('QDRANT_URL=http://localhost:6333\n')
            elif line.startswith('QDRANT_API_KEY='):
                new_lines.append('QDRANT_API_KEY=\n')
            else:
                new_lines.append(line)
        
        with open(env_file, 'w') as f:
            f.writelines(new_lines)
        
        print()
        print("✅ 本地 Qdrant 配置已保存到 .env 文件")
        
    else:
        print("❌ 无效的选择")
        return
    
    # 询问是否测试连接
    print()
    test = input("是否测试连接? (y/n): ").strip().lower()
    if test == 'y':
        print()
        print("正在测试连接...")
        
        from dotenv import load_dotenv
        load_dotenv()
        
        try:
            from qdrant_client import QdrantClient
            
            url = os.getenv('QDRANT_URL')
            key = os.getenv('QDRANT_API_KEY')
            
            if not url:
                print("❌ QDRANT_URL 未设置")
                return
            
            client = QdrantClient(url=url, api_key=key if key else None)
            collections = client.get_collections()
            
            print("✅ 连接成功！")
            print(f"   当前集合数: {len(collections.collections)}")
            
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            print()
            print("请检查:")
            print("1. QDRANT_URL 是否正确")
            print("2. QDRANT_API_KEY 是否正确（如果是 Cloud）")
            print("3. 网络连接是否正常")
    
    print()
    print("=" * 60)
    print("✅ 配置完成！")
    print("=" * 60)
    print()
    print("下一步:")
    print("1. 重启服务器: kill $(cat server.pid) && nohup python3 web_server.py --mode user --port 8000 > server.log 2>&1 &")
    print("2. 访问前端: http://localhost:8000/static/index.html")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已取消")
        sys.exit(0)
