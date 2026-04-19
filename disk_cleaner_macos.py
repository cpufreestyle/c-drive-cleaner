#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
磁盘清理工具 - macOS 版本
安全清理临时文件、缓存、日志等无用文件，释放磁盘空间
"""

import os
import sys
import shutil
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path


class DiskCleaner:
    """macOS 磁盘空间清理核心类"""

    def __init__(self):
        self.home = Path.home()
        self.total_freed = 0
        self.cleaned_items = []
        self.errors = []
        # is_admin: True = needs sudo / already running as root (will skip)
        self.clean_targets = [
            {
                "name": "系统缓存 (~/Library/Caches)",
                "path": str(self.home / "Library" / "Caches"),
                "sudo": False,
                "category": "系统"
            },
            {
                "name": "Xcode 缓存 (DerivedData)",
                "path": str(self.home / "Library" / "Developer" / "Xcode" / "DerivedData"),
                "sudo": False,
                "category": "开发"
            },
            {
                "name": "Xcode 模拟器缓存",
                "path": str(self.home / "Library" / "Developer" / "CoreSimulator" / "Devices"),
                "sudo": False,
                "category": "开发"
            },
            {
                "name": "Safari 浏览器缓存",
                "path": str(self.home / "Library" / "Caches" / "Safari"),
                "sudo": False,
                "category": "浏览器"
            },
            {
                "name": "Chrome 浏览器缓存",
                "path": str(self.home / "Library" / "Caches" / "Google" / "Chrome"),
                "sudo": False,
                "category": "浏览器"
            },
            {
                "name": "Microsoft Edge 缓存",
                "path": str(self.home / "Library" / "Caches" / "Microsoft" / "Edge"),
                "sudo": False,
                "category": "浏览器"
            },
            {
                "name": "Firefox 浏览器缓存",
                "path": str(self.home / "Library" / "Caches" / "Firefox" / "Profiles"),
                "sudo": False,
                "category": "浏览器"
            },
            {
                "name": "npm 缓存",
                "path": str(self.home / ".npm" / "_cacache"),
                "sudo": False,
                "category": "开发"
            },
            {
                "name": "pip 缓存",
                "path": str(self.home / "Library" / "Caches" / "pip"),
                "sudo": False,
                "category": "开发"
            },
            {
                "name": "Homebrew 缓存",
                "path": str(self.home / "Library" / "Caches" / "Homebrew"),
                "sudo": False,
                "category": "系统"
            },
            {
                "name": "系统日志 (~/Library/Logs)",
                "path": str(self.home / "Library" / "Logs"),
                "sudo": False,
                "category": "日志"
            },
            {
                "name": "Docker 数据 (可选)",
                "path": str(self.home / "Library" / "Containers" / "com.docker.docker" / "Data"),
                "sudo": False,
                "category": "容器"
            },
            {
                "name": "废纸篓",
                "path": str(self.home / ".Trash"),
                "sudo": False,
                "category": "系统"
            },
            {
                "name": "系统日志 (/var/log, 需要管理员)",
                "path": "/var/log",
                "sudo": True,
                "category": "日志"
            },
            {
                "name": "下载目录 (可选)",
                "path": str(self.home / "Downloads"),
                "sudo": False,
                "optional": True,
                "category": "文件"
            },
        ]

    def get_folder_size(self, path: str) -> int:
        """递归计算文件夹大小（单位：字节）"""
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
        """获取磁盘信息（macOS 版）"""
        try:
            stat = os.statvfs("/")
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            used = total - free
            return {
                "total": total,
                "used": used,
                "free": free,
                "used_percent": (used / total * 100) if total > 0 else 0
            }
        except Exception:
            return {}

    def clean_path(self, path: str) -> int:
        """清理指定路径，返回释放空间大小（字节）"""
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
            self.errors.append(f"无法访问: {path}")
        return freed


class App(tk.Tk):
    """macOS 磁盘清理工具主界面"""

    def __init__(self):
        super().__init__()
        self.title("磁盘清理工具 v2.0 (macOS)")
        self.geometry("780x700")
        self.minsize(700, 600)
        self.configure(bg="#0f0f0f")

        self._running = False
        self._cleaner = DiskCleaner()
        self._scan_results = []
        self._check_vars = {}  # name -> tk.BooleanVar

        self._build_ui()
        self._update_disk_info()
        self._apply_dark_theme()

    # ── Dark theme constants ──────────────────────────────────────────
    BG = "#0f0f0f"          # window background
    SURFACE = "#1a1a1a"     # cards / panels
    SURFACE2 = "#252525"    # listbox background
    ACCENT = "#ea580c"      # orange accent
    ACCENT2 = "#ff7b3a"     # lighter orange for hover
    TEXT = "#e0e0e0"        # primary text
    TEXT2 = "#888888"       # secondary text
    TEXT3 = "#555555"       # disabled / muted
    BORDER = "#2a2a2a"      # borders
    GREEN = "#4caf50"       # success
    YELLOW = "#f5c542"      # warning / caution
    BLUE = "#2196f3"        # info

    def _apply_dark_theme(self):
        """Force ttk dark styling."""
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure(
            "Dark.Horizontal.TProgressbar",
            troughcolor=self.SURFACE,
            background=self.ACCENT,
            thickness=8,
        )
        style.configure(
            "Dark.Treeview",
            background=self.SURFACE2,
            foreground=self.TEXT,
            fieldbackground=self.SURFACE2,
            bordercolor=self.BORDER,
        )
        style.map(
            "Dark.Horizontal.TProgressbar",
            background=[("active", self.ACCENT2)],
        )

    # ── UI building ───────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=self.SURFACE, pady=14, padx=20)
        hdr.pack(fill="x")

        tk.Label(
            hdr, text="💾  macOS 磁盘清理工具",
            font=("SF Pro Display", 17, "bold"),
            fg=self.ACCENT, bg=self.SURFACE,
        ).pack(anchor="w")

        tk.Label(
            hdr,
            text="清理缓存、日志、开发工具残留，释放磁盘空间",
            font=("SF Pro Text", 10),
            fg=self.TEXT2, bg=self.SURFACE,
        ).pack(anchor="w", pady=(2, 0))

        # ── Disk info card ───────────────────────────────────────────
        disk_card = tk.Frame(self, bg=self.SURFACE, padx=20, pady=12)
        disk_card.pack(fill="x", padx=20, pady=(10, 5))

        # Stats row
        stats = tk.Frame(disk_card, bg=self.SURFACE)
        stats.pack(fill="x")

        self._stat(stats, "💽 总容量", "lbl_total", "— GB")
        self._stat(stats, "📂 已使用", "lbl_used", "— GB")
        self._stat(stats, "🆓 可用空间", "lbl_free", "— GB")
        self._stat(stats, "🧹 可清理", "lbl_cleanable", "扫描中…")

        # Progress bar
        pb_frame = tk.Frame(disk_card, bg=self.SURFACE, pady=(10, 0))
        pb_frame.pack(fill="x")
        self.progress_bar = ttk.Progressbar(
            pb_frame,
            mode="determinate",
            style="Dark.Horizontal.TProgressbar",
        )
        self.progress_bar.pack(fill="x")

        # ── Category filter row ──────────────────────────────────────
        filter_frame = tk.Frame(self, bg=self.BG, padx=20, pady=(5, 0))
        filter_frame.pack(fill="x")

        tk.Label(
            filter_frame, text="分类:",
            font=("SF Pro Text", 10), fg=self.TEXT2, bg=self.BG,
        ).pack(side="left", padx=(0, 8))

        self._filter_btn(filter_frame, "全部", "all")
        self._filter_btn(filter_frame, "系统", "系统")
        self._filter_btn(filter_frame, "开发", "开发")
        self._filter_btn(filter_frame, "浏览器", "浏览器")
        self._filter_btn(filter_frame, "日志", "日志")
        self._filter_btn(filter_frame, "容器", "容器")
        self._filter_btn(filter_frame, "文件", "文件")
        self._active_filter = "all"

        # ── Cleanup list ─────────────────────────────────────────────
        list_frame = tk.Frame(self, bg=self.BG, padx=20, pady=(5, 0))
        list_frame.pack(fill="both", expand=True, pady=(5, 0))

        # column headers
        hdr_row = tk.Frame(list_frame, bg=self.SURFACE)
        hdr_row.pack(fill="x")
        tk.Label(hdr_row, text="  ☐", font=("SF Pro Text", 10, "bold"),
                 fg=self.TEXT2, bg=self.SURFACE, width=3).pack(side="left")
        tk.Label(hdr_row, text="类别", font=("SF Pro Text", 9, "bold"),
                 fg=self.TEXT2, bg=self.SURFACE, width=8).pack(side="left")
        tk.Label(hdr_row, text="清理项目", font=("SF Pro Text", 9, "bold"),
                 fg=self.TEXT2, bg=self.SURFACE).pack(side="left")
        tk.Label(hdr_row, text="大小", font=("SF Pro Text", 9, "bold"),
                 fg=self.TEXT2, bg=self.SURFACE, width=12).pack(side="right")

        # scrollable list
        container = tk.Frame(list_frame, bg=self.SURFACE2)
        container.pack(fill="both", expand=True, pady=(2, 0))

        scrollbar = tk.Scrollbar(container)
        scrollbar.pack(side="right", fill="y")

        self.canvas_list = tk.Canvas(
            container, bg=self.SURFACE2,
            highlightthickness=0, bd=0,
        )
        self.canvas_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.canvas_list.yview)

        self.inner_frame = tk.Frame(self.canvas_list, bg=self.SURFACE2)
        self.canvas_list.create_window((0, 0), window=self.inner_frame, anchor="nw")
        self.canvas_list.config(yscrollcommand=scrollbar.set)

        self.inner_frame.bind(
            "<Configure>",
            lambda e: self.canvas_list.configure(scrollregion=self.canvas_list.bbox("all")),
        )
        # Mousewheel
        self.canvas_list.bind_all(
            "<MouseWheel>",
            lambda e: self.canvas_list.yview_scroll(int(-1 * (e.delta / 120)), "units"),
        )

        # ── Log output ───────────────────────────────────────────────
        log_hdr = tk.Frame(self, bg=self.BG, padx=20, pady=(5, 0))
        log_hdr.pack(fill="x")
        tk.Label(
            log_hdr, text="📋 清理日志",
            font=("SF Pro Text", 10, "bold"), fg=self.TEXT2, bg=self.BG,
        ).pack(anchor="w")

        log_container = tk.Frame(self, bg=self.SURFACE2, padx=10, pady=5)
        log_container.pack(fill="x", padx=20, pady=(0, 5))

        log_scroll = tk.Scrollbar(log_container)
        log_scroll.pack(side="right", fill="y")

        self.log_box = tk.Text(
            log_container,
            font=("Menlo", 9),
            bg=self.SURFACE2, fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat", bd=0,
            height=5,
            state="disabled",
            yscrollcommand=log_scroll.set,
        )
        self.log_box.pack(fill="x", expand=True)
        log_scroll.config(command=self.log_box.yview)

        # ── Bottom buttons ───────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=self.BG, pady=12)
        btn_frame.pack()

        self.btn_scan = self._btn(
            btn_frame, "🔍  扫描",
            lambda: self._scan(),
            bg=self.ACCENT, fg="white",
        )
        self.btn_scan.pack(side="left", padx=6)

        self.btn_clean = self._btn(
            btn_frame, "🧹  清理选中",
            lambda: self._clean(),
            bg=self.GREEN, fg="white",
            state="disabled",
        )
        self.btn_clean.pack(side="left", padx=6)

        self.btn_select_all = self._btn(
            btn_frame, "☑  全选",
            lambda: self._select_all(),
            bg=self.SURFACE, fg=self.TEXT,
            state="disabled",
        )
        self.btn_select_all.pack(side="left", padx=6)

        self.btn_deselect = self._btn(
            btn_frame, "☐  取消全选",
            lambda: self._deselect_all(),
            bg=self.SURFACE, fg=self.TEXT,
            state="disabled",
        )
        self.btn_deselect.pack(side="left", padx=6)

    # ── Widget factories ──────────────────────────────────────────────
    def _stat(self, parent, label, key, initial):
        f = tk.Frame(parent, bg=self.SURFACE, padx=12, pady=4)
        f.pack(side="left", padx=4)
        tk.Label(
            f, text=label,
            font=("SF Pro Text", 9), fg=self.TEXT2, bg=self.SURFACE,
        ).pack()
        lbl = tk.Label(
            f, text=initial,
            font=("SF Pro Display", 13, "bold"),
            fg=self.TEXT, bg=self.SURFACE,
        )
        lbl.pack()
        setattr(self, key, lbl)

    def _filter_btn(self, parent, text, tag):
        b = tk.Button(
            parent, text=text,
            font=("SF Pro Text", 9),
            bg=self.SURFACE, fg=self.TEXT2,
            relief="flat", bd=0, padx=10, pady=3,
            cursor="hand2",
            command=lambda: self._set_filter(tag),
        )
        b.pack(side="left", padx=3)
        setattr(self, f"btn_filter_{tag}", b)

    def _btn(self, parent, text, command, bg, fg, state="normal", width=14):
        return tk.Button(
            parent, text=text,
            font=("SF Pro Text", 11, "bold"),
            bg=bg, fg=fg,
            activebackground=bg, activeforeground=fg,
            relief="flat", bd=0,
            padx=14, pady=6,
            width=width,
            state=state,
            cursor="hand2",
            command=command,
        )

    def _item_row(self, target: dict, size_str: str, var: tk.BooleanVar):
        """Create one row inside inner_frame. Returns the row Frame."""
        is_sudo = target.get("sudo", False)
        is_optional = target.get("optional", False)
        cat = target.get("category", "")
        name = target["name"]

        row = tk.Frame(self.inner_frame, bg=self.SURFACE2, pady=1)
        row.pack(fill="x")

        # alternating shade
        shade = "#202020" if self.inner_frame.winfo_children()[-1:][0].winfo_children() else self.SURFACE2

        # Checkbox
        cb = tk.Checkbutton(
            row, variable=var,
            bg=self.SURFACE2,
            activebackground=self.SURFACE2,
            selectcolor=self.SURFACE2,
            fg=self.ACCENT,
            font=("SF Pro Text", 10),
        )
        cb.pack(side="left", padx=(6, 2))

        # Category badge
        cat_color = {
            "系统": "#4a9eff",
            "开发": "#a78bfa",
            "浏览器": "#34d399",
            "日志": "#fbbf24",
            "容器": "#f87171",
            "文件": "#94a3b8",
        }.get(cat, "#888")
        cat_lbl = tk.Label(
            row, text=cat,
            font=("SF Pro Text", 8),
            fg="white", bg=cat_color,
            padx=5, pady=1,
        )
        cat_lbl.pack(side="left", padx=(0, 6))

        # Name
        suffix = ""
        if is_sudo:
            suffix = "  ⚠️ 需要管理员"
        elif is_optional:
            suffix = "  ⭐ 可选"

        name_lbl = tk.Label(
            row, text=name + suffix,
            font=("SF Pro Text", 10),
            fg=self.YELLOW if is_sudo else self.TEXT,
            bg=self.SURFACE2,
            anchor="w",
        )
        name_lbl.pack(side="left", fill="x", expand=True)

        # Size
        size_lbl = tk.Label(
            row, text=size_str,
            font=("Menlo", 10),
            fg=self.ACCENT, bg=self.SURFACE2,
            width=12, anchor="e",
        )
        size_lbl.pack(side="right", padx=(0, 8))

        # separator
        sep = tk.Frame(self.inner_frame, bg=self.BORDER, height=1)
        sep.pack(fill="x")

        return row

    # ── Filtering ─────────────────────────────────────────────────────
    def _set_filter(self, tag):
        self._active_filter = tag
        for cat, btn in [
            ("all", self.btn_filter_all), ("系统", self.btn_filter_系统),
            ("开发", self.btn_filter_开发), ("浏览器", self.btn_filter_浏览器),
            ("日志", self.btn_filter_日志), ("容器", self.btn_filter_容器),
            ("文件", self.btn_filter_文件),
        ]:
            active = cat == tag
            btn.config(
                bg=self.ACCENT if active else self.SURFACE,
                fg="white" if active else self.TEXT2,
            )
        self._apply_filter()

    def _apply_filter(self):
        for child in list(self.inner_frame.children.values()):
            child.destroy() if hasattr(child, 'destroy') else None
        self._check_vars.clear()
        for result in self._scan_results:
            target = result["target"]
            if self._active_filter != "all" and target.get("category") != self._active_filter:
                continue
            var = tk.BooleanVar(value=result.get("checked", False))
            self._check_vars[result["name"]] = var
            self._item_row(target, result["size_str"], var)
        self._refresh_sep()

    def _refresh_sep(self):
        """Re-add separators after rows."""
        pass  # separators are created inside _item_row via inner_frame

    # ── Logging ───────────────────────────────────────────────────────
    def _log(self, msg, color=None):
        color_map = {
            "green": "#4caf50",
            "yellow": "#f5c542",
            "red": "#f87171",
            "blue": "#2196f3",
            "orange": self.ACCENT,
        }
        c = color_map.get(color, self.TEXT)
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n", c)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # ── Disk info ─────────────────────────────────────────────────────
    def _update_disk_info(self):
        disk = self._cleaner.get_disk_info()
        if disk:
            self.lbl_total.config(
                text=self._cleaner.format_size(disk["total"])
            )
            self.lbl_used.config(
                text=f"{self._cleaner.format_size(disk['used'])} ({disk['used_percent']:.1f}%)"
            )
            self.lbl_free.config(text=self._cleaner.format_size(disk["free"]))
            self.progress_bar["value"] = disk["used_percent"]

    # ── Scanning ──────────────────────────────────────────────────────
    def _scan(self):
        if self._running:
            return
        self._running = True
        self._set_buttons_scan()
        self._log("🔍  开始扫描可清理文件…", "blue")
        self._clear_rows()
        self.lbl_cleanable.config(text="扫描中…")
        threading.Thread(target=self._do_scan, daemon=True).start()

    def _set_buttons_scan(self):
        self.btn_scan.config(state="disabled")
        self.btn_clean.config(state="disabled")
        self.btn_select_all.config(state="disabled")
        self.btn_deselect.config(state="disabled")

    def _set_buttons_idle(self):
        self.btn_scan.config(state="normal")
        self.btn_select_all.config(state="normal")
        self.btn_deselect.config(state="normal")

    def _clear_rows(self):
        for child in list(self.inner_frame.winfo_children()) if hasattr(self.inner_frame, 'winfo_children') else []:
            try:
                child.destroy()
            except Exception:
                pass

    def _do_scan(self):
        total_size = 0
        for target in self._cleaner.clean_targets:
            path = target["path"]
            if os.path.exists(path):
                size = self._cleaner.get_folder_size(path)
                size_str = self._cleaner.format_size(size)
                if size > 0:
                    total_size += size
                    result = {"name": target["name"], "path": path,
                              "size": size, "size_str": size_str,
                              "target": target, "checked": True}
                    self._scan_results.append(result)
                    self.after(0, lambda r=result: self._add_scan_row(r))
            else:
                # path doesn't exist – skip silently
                pass

        self.after(0, lambda: self._scan_done(total_size))

    def _add_scan_row(self, result):
        target = result["target"]
        var = tk.BooleanVar(value=result.get("checked", True))
        self._check_vars[result["name"]] = var
        self._item_row(target, result["size_str"], var)
        self._log(f"  📦 {target.get('category','?'):6s}  {result['size_str']:>10s}  {result['name']}", "orange")

    def _scan_done(self, total_size):
        self._running = False
        self._set_buttons_idle()
        self.lbl_cleanable.config(text=self._cleaner.format_size(total_size))
        self._log(f"\n✅  扫描完成，可清理总计: {self._cleaner.format_size(total_size)}", "green")
        self._log("ℹ️  勾选要清理的项目，点击「清理选中」开始清理。", "blue")
        if self._scan_results:
            self.btn_clean.config(state="normal")
        else:
            self._log("🎉  磁盘已经很干净！", "green")

    # ── Selection ─────────────────────────────────────────────────────
    def _select_all(self):
        for var in self._check_vars.values():
            var.set(True)

    def _deselect_all(self):
        for var in self._check_vars.values():
            var.set(False)

    # ── Cleaning ──────────────────────────────────────────────────────
    def _clean(self):
        if self._running:
            return
        selected = [
            r for r in self._scan_results
            if self._check_vars.get(r["name"], tk.BooleanVar()).get()
        ]
        if not selected:
            messagebox.showwarning("提示", "请先勾选要清理的项目")
            return

        total = sum(r["size"] for r in selected)
        sudo_items = [r for r in selected if r["target"].get("sudo", False)]

        if sudo_items and os.geteuid() != 0:
            warn = (
                f"以下项目需要管理员权限，当前无法清理：\n\n"
                + "\n".join(f"  ⚠️  {r['name']}" for r in sudo_items)
                + "\n\n跳过这些项目，继续清理其他？"
            )
            if not messagebox.askyesno("需要管理员权限", warn):
                return
            selected = [r for r in selected if not r["target"].get("sudo", False)]
            if not selected:
                return

        confirm = (
            f"即将释放 {self._cleaner.format_size(total)} 空间\n\n"
            f"确定要清理选中的 {len(selected)} 个项目吗？"
        )
        if not messagebox.askyesno("确认清理", confirm):
            return

        self._running = True
        self._set_buttons_scan()
        self._cleaner.total_freed = 0
        self._cleaner.errors = []

        self._log(f"\n🧹  开始清理 {len(selected)} 个项目…\n", "orange")
        threading.Thread(target=self._do_clean, args=(selected,), daemon=True).start()

    def _do_clean(self, selected):
        total_freed = 0
        for result in selected:
            target = result["target"]
            path = result["path"]
            self.after(0, lambda r=result: self._log(
                f"  → 正在清理: {r['name']}…", "blue"
            ))
            freed = self._cleaner.clean_path(path)
            total_freed += freed
            if freed > 0:
                self.after(0, lambda f=freed: self._log(
                    f"      ✓ 释放 {self._cleaner.format_size(f)}", "green"
                ))
            else:
                self.after(0, lambda n=result["name"]: self._log(
                    f"      ○ 无变化: {n}", "yellow"
                ))

        self._cleaner.total_freed = total_freed
        self.after(0, lambda: self._clean_done(total_freed))

    def _clean_done(self, total_freed):
        self._running = False
        self._set_buttons_idle()
        self._log(f"\n{'─' * 50}", "green")
        self._log(f"🎉  清理完成！总计释放: {self._cleaner.format_size(total_freed)}", "green")
        self._log(f"{'─' * 50}", "green")

        if self._cleaner.errors:
            err_str = "\n".join(self._cleaner.errors[:5])
            self._log(f"\n⚠️  跳过以下文件（权限不足）:\n{err_str}", "yellow")

        self._update_disk_info()
        self._scan_results = []
        self._check_vars.clear()
        for child in list(self.inner_frame.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass
        self.lbl_cleanable.config(text="—")
        self.btn_clean.config(state="disabled")


# ── Entry point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
