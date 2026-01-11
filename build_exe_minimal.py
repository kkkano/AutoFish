#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻量级 exe 打包脚本 - 最小化文件体积

使用说明:
  1. 确保已安装 PyInstaller: pip install pyinstaller
  2. 可选：安装 UPX 以获得更小的文件: https://upx.github.io/
  3. 运行本脚本: python build_exe_minimal.py
  
优化策略:
  - 移除不必要的模块 (numpy, scipy, pandas 等)
  - 启用 UPX 压缩 (需要单独安装)
  - 移除调试符号 (strip=True)
  - Python 字节码优化 (optimize=2)
  - 单文件打包 (onefile=True) 可选，体积会更小但启动较慢
"""

import os
import sys
import shutil
import subprocess

def run_command(cmd, description=""):
    """运行命令并显示进度"""
    print(f"\n{'='*60}")
    if description:
        print(f"📦 {description}")
    print(f"{'='*60}")
    print(f"$ {cmd}\n")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌ 命令执行失败: {cmd}")
        sys.exit(1)
    return result.returncode

def clean_build_artifacts():
    """清理之前的构建文件"""
    print("\n🧹 清理之前的构建文件...")
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"  ✓ 删除 {folder}/")

def check_upx():
    """检查 UPX 是否可用"""
    try:
        result = subprocess.run(['upx', '--version'], capture_output=True)
        if result.returncode == 0:
            print("✅ 已检测到 UPX 压缩工具")
            return True
    except:
        pass
    print("⚠️  未检测到 UPX，将使用默认压缩（建议安装 UPX 以获得更小的文件）")
    print("   下载地址: https://upx.github.io/")
    return False

def build_exe():
    """构建 exe"""
    print("\n🔨 开始构建 exe...")
    
    # 基础命令
    cmd = "pyinstaller LoafOnTheJob.spec"
    
    run_command(cmd, "运行 PyInstaller...")

def optimize_dist():
    """优化输出目录"""
    print("\n🔍 优化输出文件...")
    
    dist_dir = 'dist'
    if not os.path.exists(dist_dir):
        print("❌ dist 目录不存在")
        return
    
    # 统计文件大小
    def get_dir_size(path):
        total = 0
        for entry in os.scandir(path):
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
        return total
    
    total_size = get_dir_size(dist_dir)
    size_mb = total_size / (1024 * 1024)
    
    print(f"\n✅ 打包完成！")
    print(f"   输出目录: {os.path.abspath(dist_dir)}")
    print(f"   总大小: {size_mb:.2f} MB")
    
    # 查找 exe 文件
    exe_file = os.path.join(dist_dir, 'LoafOnTheJob.exe')
    if os.path.exists(exe_file):
        exe_size = os.path.getsize(exe_file) / (1024 * 1024)
        print(f"   主程序: LoafOnTheJob.exe ({exe_size:.2f} MB)")

def main():
    """主函数"""
    print(r"""
    ╔═══════════════════════════════════════════════════════════╗
    ║        AutoFish 轻量级打包工具                             ║
    ║                                                           ║
    ║   智能办公助手 - 最小化 exe 文件                            ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # 检查环境
    check_upx()
    
    # 清理旧文件
    clean_build_artifacts()
    
    # 构建 exe
    build_exe()
    
    # 优化输出
    optimize_dist()
    
    print("\n" + "="*60)
    print("🎉 打包完成！")
    print("="*60)
    print(f"\n📂 可执行文件位置:")
    print(f"   {os.path.abspath(os.path.join('dist', 'LoafOnTheJob.exe'))}")
    print(f"\n💡 下次优化建议:")
    print(f"   1. 安装 UPX 压缩工具")
    print(f"   2. 修改 LoafOnTheJob.spec 中的 onefile=True")
    print(f"   3. 删除不必要的依赖库\n")

if __name__ == '__main__':
    main()
