#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C盘空间清理工具
安全清理临时文件、缓存、日志等无用文件，释放C盘空间
"""

import os
import sys
import io
import shutil
import tempfile
import ctypes
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class CDriveCleaner:
    """C盘空间清理工具"""
    
    def __init__(self):
        self.total_freed = 0
        self.cleaned_items = []
        self.errors = []
        
        # 安全清理目标列表
        self.clean_targets = [
            {
                "name": "Windows 临时文件",
                "path": os.environ.get("TEMP", "C:\\Windows\\Temp"),
                "pattern": "*",
                "safe": True
            },
            {
                "name": "系统临时文件",
                "path": "C:\\Windows\\Temp",
                "pattern": "*",
                "safe": True
            },
            {
                "name": "用户临时文件",
                "path": os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Temp"),
                "pattern": "*",
                "safe": True
            },
            {
                "name": "缩略图缓存",
                "path": os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Microsoft", "Windows", "Explorer"),
                "pattern": "thumbcache_*.db",
                "safe": True
            },
            {
                "name": "Windows 更新缓存",
                "path": "C:\\Windows\\SoftwareDistribution\\Download",
                "pattern": "*",
                "safe": True
            },
            {
                "name": "预取文件",
                "path": "C:\\Windows\\Prefetch",
                "pattern": "*.pf",
                "safe": True
            },
            {
                "name": "错误报告文件",
                "path": os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Microsoft", "Windows", "WER"),
                "pattern": "*",
                "safe": True
            },
            {
                "name": "浏览器缓存 (Edge)",
                "path": os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Cache"),
                "pattern": "*",
                "safe": True
            },
            {
                "name": "浏览器缓存 (Chrome)",
                "path": os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Cache"),
                "pattern": "*",
                "safe": True
            },
        ]
    
    def get_folder_size(self, path: str) -> int:
        """获取文件夹大小（字节）"""
        total = 0
        try:
            for entry in os.scandir(path):
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat().st_size
                    elif entry.is_dir(follow_symlinks=False):
                        total += self.get_folder_size(entry.path)
                except (PermissionError, OSError):
                    pass
        except (PermissionError, OSError):
            pass
        return total
    
    def format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def get_disk_info(self) -> dict:
        """获取C盘磁盘信息"""
        try:
            total, used, free = shutil.disk_usage("C:\\")
            return {
                "total": total,
                "used": used,
                "free": free,
                "used_percent": used / total * 100
            }
        except Exception as e:
            return {}
    
    def scan(self) -> list:
        """扫描可清理的文件"""
        print("\n🔍 正在扫描可清理文件...")
        print("=" * 60)
        
        scan_results = []
        
        for target in self.clean_targets:
            path = target["path"]
            if not os.path.exists(path):
                continue
            
            size = self.get_folder_size(path)
            if size > 0:
                scan_results.append({
                    "name": target["name"],
                    "path": path,
                    "size": size,
                    "size_str": self.format_size(size),
                    "safe": target["safe"]
                })
                print(f"  ✓ {target['name']}: {self.format_size(size)}")
        
        total_size = sum(r["size"] for r in scan_results)
        print(f"\n📊 可清理总计: {self.format_size(total_size)}")
        
        return scan_results
    
    def clean_path(self, path: str) -> int:
        """清理指定路径，返回释放的字节数"""
        freed = 0
        
        if not os.path.exists(path):
            return 0
        
        try:
            for item in os.scandir(path):
                try:
                    item_size = 0
                    if item.is_file(follow_symlinks=False):
                        item_size = item.stat().st_size
                        os.unlink(item.path)
                        freed += item_size
                    elif item.is_dir(follow_symlinks=False):
                        item_size = self.get_folder_size(item.path)
                        shutil.rmtree(item.path, ignore_errors=True)
                        freed += item_size
                except (PermissionError, OSError) as e:
                    self.errors.append(f"跳过: {item.path} ({str(e)[:50]})")
        except (PermissionError, OSError) as e:
            self.errors.append(f"无法访问: {path} (需要管理员权限)")
        
        return freed
    
    def clean(self, targets: list = None) -> int:
        """执行清理操作"""
        if targets is None:
            targets = self.clean_targets
        
        print("\n🧹 开始清理...")
        print("=" * 60)
        
        total_freed = 0
        
        for target in targets:
            path = target["path"]
            if not os.path.exists(path):
                continue
            
            print(f"  清理: {target['name']}...", end=" ")
            freed = self.clean_path(path)
            total_freed += freed
            
            if freed > 0:
                print(f"✓ 释放 {self.format_size(freed)}")
                self.cleaned_items.append({
                    "name": target["name"],
                    "freed": freed
                })
            else:
                print("(无可清理文件)")
        
        self.total_freed = total_freed
        return total_freed
    
    def generate_report(self) -> str:
        """生成清理报告"""
        report = []
        report.append("\n" + "=" * 60)
        report.append("📋 清理报告")
        report.append("=" * 60)
        report.append(f"清理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"总计释放: {self.format_size(self.total_freed)}")
        report.append("")
        
        if self.cleaned_items:
            report.append("清理详情:")
            for item in self.cleaned_items:
                report.append(f"  ✓ {item['name']}: {self.format_size(item['freed'])}")
        
        if self.errors:
            report.append(f"\n跳过文件 ({len(self.errors)} 个):")
            for err in self.errors[:5]:
                report.append(f"  • {err}")
            if len(self.errors) > 5:
                report.append(f"  ... 还有 {len(self.errors) - 5} 个")
        
        # 清理后磁盘信息
        disk = self.get_disk_info()
        if disk:
            report.append(f"\nC盘当前状态:")
            report.append(f"  总容量: {self.format_size(disk['total'])}")
            report.append(f"  已使用: {self.format_size(disk['used'])} ({disk['used_percent']:.1f}%)")
            report.append(f"  可用空间: {self.format_size(disk['free'])}")
        
        report.append("=" * 60)
        return "\n".join(report)


def main():
    """主函数"""
    print("=" * 60)
    print("   🧹 C盘空间清理工具 v1.0")
    print("=" * 60)
    
    cleaner = CDriveCleaner()
    
    # 显示当前磁盘状态
    disk = cleaner.get_disk_info()
    if disk:
        print(f"\nC盘当前状态:")
        print(f"  总容量: {cleaner.format_size(disk['total'])}")
        print(f"  已使用: {cleaner.format_size(disk['used'])} ({disk['used_percent']:.1f}%)")
        print(f"  可用空间: {cleaner.format_size(disk['free'])}")
    
    # 扫描
    scan_results = cleaner.scan()
    
    if not scan_results:
        print("\n✅ C盘已经很干净，无需清理！")
        return
    
    # 询问用户
    print("\n是否开始清理？(y/n): ", end="")
    try:
        choice = input().strip().lower()
    except:
        choice = 'y'
    
    if choice == 'y':
        cleaner.clean()
        print(cleaner.generate_report())
    else:
        print("\n已取消清理。")


if __name__ == "__main__":
    main()
