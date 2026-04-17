#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C盘空间清理工具 - GUI 版本
安全清理临时文件、缓存、日志等无用文件，释放C盘空间
"""

import os
import sys
import shutil
import ctypes
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime


class CDriveCleaner:
    """C盘空间清理核心类"""
    
    def __init__(self):
        self.total_freed = 0
        self.cleaned_items = []
        self.errors = []
        self.clean_targets = [
            {"name": "Windows 临时文件", "path": os.environ.get("TEMP", "C:\\Windows\\Temp"), "safe": True},
            {"name": "系统临时文件", "path": "C:\\Windows\\Temp", "safe": True},
            {"name": "用户临时文件", "path": os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Temp"), "safe": True},
            {"name": "缩略图缓存", "path": os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Microsoft", "Windows", "Explorer"), "pattern": "thumbcache_*.db", "safe": True},
            {"name": "Windows 更新缓存", "path": "C:\\Windows\\SoftwareDistribution\\Download", "safe": True},
            {"name": "预取文件", "path": "C:\\Windows\\Prefetch", "safe": True},
            {"name": "错误报告文件", "path": os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Microsoft", "Windows", "WER"), "safe": True},
            {"name": "浏览器缓存 (Edge)", "path": os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Cache"), "safe": True},
            {"name": "浏览器缓存 (Chrome)", "path": os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Cache"), "safe": True},
            {"name": "回收站", "path": "C:\\$Recycle.Bin", "safe": True},
            {"name": "Windows 日志", "path": "C:\\Windows\\Logs", "safe": True},
            {"name": "Windows 旧版本备份", "path": "C:\\Windows.old", "safe": False},
        ]
    
    def get_folder_size(self, path: str) -> int:
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
    
    @staticmethod
    def format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def get_disk_info(self) -> dict:
        try:
            total, used, free = shutil.disk_usage("C:\\")
            return {"total": total, "used": used, "free": free, "used_percent": used / total * 100}
        except Exception:
            return {}
    
    def clean_path(self, path: str) -> int:
        freed = 0
        if not os.path.exists(path):
            return 0
        try:
            for item in os.scandir(path):
                try:
                    if item.is_file(follow_symlinks=False):
                        item_size = item.stat().st_size
                        os.unlink(item.path)
                        freed += item_size
                    elif item.is_dir(follow_symlinks=False):
                        item_size = self.get_folder_size(item.path)
                        shutil.rmtree(item.path, ignore_errors=True)
                        freed += item_size
                except (PermissionError, OSError) as e:
                    self.errors.append(f"跳过: {item.path}")
        except (PermissionError, OSError):
            self.errors.append(f"无法访问: {path} (需要管理员权限)")
        return freed


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("C盘空间清理工具 v2.0")
        self.geometry("750x650")
        self.resizable(True, True)
        self.configure(bg="#1e1e2e")
        self._running = False
        self._cleaner = CDriveCleaner()
        self._scan_results = []
        self._build_ui()
        self._update_disk_info()
    
    def _build_ui(self):
        # 标题
        header = tk.Frame(self, bg="#313244", pady=12)
        header.pack(fill="x")
        tk.Label(header, text="🧹 C盘空间清理工具", font=("微软雅黑", 16, "bold"), fg="#cdd6f4", bg="#313244").pack()
        tk.Label(header, text="安全清理临时文件、缓存、日志等，释放磁盘空间", font=("微软雅黑", 9), fg="#a6adc8", bg="#313244").pack()
        
        # 磁盘状态卡片
        disk_frame = tk.Frame(self, bg="#313244", pady=10, padx=15)
        disk_frame.pack(fill="x", padx=20, pady=10)
        
        self.lbl_total = self._disk_stat(disk_frame, "总容量", "0 GB")
        self.lbl_used = self._disk_stat(disk_frame, "已使用", "0 GB")
        self.lbl_free = self._disk_stat(disk_frame, "可用空间", "0 GB")
        self.lbl_cleanable = self._disk_stat(disk_frame, "可清理", "扫描中...")
        
        # 进度条
        self.progress_bar = ttk.Progressbar(disk_frame, mode="determinate", style="green.Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", pady=(10, 0))
        
        # 清理项目列表
        list_frame = tk.Frame(self, bg="#1e1e2e")
        list_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        tk.Label(list_frame, text="清理项目 (勾选要清理的项目):", font=("微软雅黑", 10), fg="#cdd6f4", bg="#1e1e2e").pack(anchor="w")
        
        # 带滚动条的列表
        list_container = tk.Frame(list_frame, bg="#181825")
        list_container.pack(fill="both", expand=True, pady=5)
        
        scrollbar = tk.Scrollbar(list_container)
        scrollbar.pack(side="right", fill="y")
        
        self.listbox = tk.Listbox(list_container, font=("微软雅黑", 10), bg="#181825", fg="#cdd6f4",
                                   selectbackground="#45475a", selectforeground="#cdd6f4",
                                   relief="flat", bd=0, height=8, selectmode="multiple",
                                   yscrollcommand=scrollbar.set)
        self.listbox.pack(fill="both", expand=True, padx=5, pady=5)
        scrollbar.config(command=self.listbox.yview)
        
        # 日志
        tk.Label(list_frame, text="清理日志:", font=("微软雅黑", 10), fg="#cdd6f4", bg="#1e1e2e").pack(anchor="w", pady=(10, 0))
        
        log_container = tk.Frame(list_frame, bg="#181825")
        log_container.pack(fill="both", expand=True, pady=5)
        
        log_scroll = tk.Scrollbar(log_container)
        log_scroll.pack(side="right", fill="y")
        
        self.log_box = tk.Text(log_container, font=("Consolas", 9), bg="#181825", fg="#cdd6f4",
                               insertbackground="#cdd6f4", relief="flat", bd=0,
                               height=6, state="disabled", yscrollcommand=log_scroll.set)
        self.log_box.pack(fill="both", expand=True, padx=5, pady=5)
        log_scroll.config(command=self.log_box.yview)
        
        # 按钮
        btn_frame = tk.Frame(self, bg="#1e1e2e", pady=10)
        btn_frame.pack()
        
        self.btn_scan = tk.Button(btn_frame, text="🔍 扫描", font=("微软雅黑", 11, "bold"),
                                   bg="#89b4fa", fg="#1e1e2e", relief="flat", padx=20, pady=6,
                                   command=self._scan)
        self.btn_scan.pack(side="left", padx=5)
        
        self.btn_clean = tk.Button(btn_frame, text="🧹 清理选中", font=("微软雅黑", 11),
                                    bg="#a6e3a1", fg="#1e1e2e", relief="flat", padx=20, pady=6,
                                    state="disabled", command=self._clean)
        self.btn_clean.pack(side="left", padx=5)
        
        self.btn_select_all = tk.Button(btn_frame, text="✅ 全选", font=("微软雅黑", 11),
                                         bg="#f9e2af", fg="#1e1e2e", relief="flat", padx=20, pady=6,
                                         state="disabled", command=self._select_all)
        self.btn_select_all.pack(side="left", padx=5)
        
        # 样式
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("green.Horizontal.TProgressbar", troughcolor="#313244", background="#a6e3a1", thickness=12)
    
    def _disk_stat(self, parent, title, value):
        f = tk.Frame(parent, bg="#313244", padx=15, pady=5)
        f.pack(side="left", padx=5)
        tk.Label(f, text=title, font=("微软雅黑", 9), fg="#a6adc8", bg="#313244").pack()
        lbl = tk.Label(f, text=value, font=("微软雅黑", 14, "bold"), fg="#cdd6f4", bg="#313244")
        lbl.pack()
        return lbl
    
    def _log(self, msg, color="#cdd6f4"):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
    
    def _update_disk_info(self):
        disk = self._cleaner.get_disk_info()
        if disk:
            self.lbl_total.config(text=self._cleaner.format_size(disk["total"]))
            self.lbl_used.config(text=f"{self._cleaner.format_size(disk['used'])} ({disk['used_percent']:.1f}%)")
            self.lbl_free.config(text=self._cleaner.format_size(disk["free"]))
            self.progress_bar["value"] = disk["used_percent"]
    
    def _scan(self):
        if self._running:
            return
        self._running = True
        self.btn_scan.config(state="disabled")
        self.btn_clean.config(state="disabled")
        self.btn_select_all.config(state="disabled")
        self.listbox.delete(0, tk.END)
        self._scan_results = []
        self._log("🔍 开始扫描可清理文件...")
        threading.Thread(target=self._do_scan, daemon=True).start()
    
    def _do_scan(self):
        total_size = 0
        for target in self._cleaner.clean_targets:
            path = target["path"]
            if os.path.exists(path):
                size = self._cleaner.get_folder_size(path)
                if size > 0:
                    size_str = self._cleaner.format_size(size)
                    self._scan_results.append({"name": target["name"], "path": path, "size": size, "safe": target["safe"]})
                    self.after(0, lambda s=size_str, n=target["name"]: self._add_scan_item(s, n))
                    total_size += size
        
        self.after(0, lambda: self._scan_done(total_size))
    
    def _add_scan_item(self, size_str, name):
        self.listbox.insert(tk.END, f"  {size_str:>10}    {name}")
    
    def _scan_done(self, total_size):
        self._running = False
        self.btn_scan.config(state="normal")
        self.lbl_cleanable.config(text=self._cleaner.format_size(total_size))
        self._log(f"📊 扫描完成，可清理: {self._cleaner.format_size(total_size)}")
        if self._scan_results:
            self.btn_clean.config(state="normal")
            self.btn_select_all.config(state="normal")
        else:
            self._log("✅ C盘已经很干净！")
    
    def _select_all(self):
        self.listbox.select_set(0, tk.END)
    
    def _clean(self):
        if self._running:
            return
        
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要清理的项目")
            return
        
        selected_names = [self._scan_results[i]["name"] for i in selection]
        total = sum(self._scan_results[i]["size"] for i in selection)
        
        if not messagebox.askyesno("确认清理", f"即将释放 {self._cleaner.format_size(total)} 空间\n\n确定要清理选中的 {len(selection)} 个项目吗？"):
            return
        
        self._running = True
        self.btn_scan.config(state="disabled")
        self.btn_clean.config(state="disabled")
        self.btn_select_all.config(state="disabled")
        self._cleaner.cleaned_items = []
        self._cleaner.errors = []
        self._cleaner.total_freed = 0
        
        self._log(f"\n🧹 开始清理 {len(selection)} 个项目...")
        threading.Thread(target=self._do_clean, args=(selection,), daemon=True).start()
    
    def _do_clean(self, selection):
        total_freed = 0
        for idx in selection:
            target = self._scan_results[idx]
            self.after(0, lambda n=target["name"]: self._log(f"  清理: {n}..."))
            freed = self._cleaner.clean_path(target["path"])
            total_freed += freed
            if freed > 0:
                self.after(0, lambda f=freed: self._log(f"    ✓ 释放 {self._cleaner.format_size(f)}", "#a6e3a1"))
        
        self._cleaner.total_freed = total_freed
        self.after(0, lambda: self._clean_done(total_freed))
    
    def _clean_done(self, total_freed):
        self._running = False
        self.btn_scan.config(state="normal")
        self.btn_clean.config(state="disabled")
        self.btn_select_all.config(state="disabled")
        
        self._log(f"\n{'='*50}")
        self._log(f"🎉 清理完成！总计释放: {self._cleaner.format_size(total_freed)}", "#a6e3a1")
        self._log(f"{'='*50}")
        
        self._update_disk_info()
        self.listbox.delete(0, tk.END)
        self._scan_results = []


if __name__ == "__main__":
    app = App()
    app.mainloop()
