# macOS 磁盘清理工具 — 任务完成记录

**时间**: 2026-04-19 20:20 GMT+8  
**任务**: 为 Windows 版 C盘清理工具创建 macOS 版本  
**输出文件**: `C:\Users\michael\.qclaw\workspace\cdrive-cleaner\disk_cleaner_macos.py`

---

## 做了什么

参考了同目录下的 `cleaner_gui.py`（Windows 版）进行移植，创建了 667 行 / 28.3 KB 的 macOS 版本。

## 主要改动对照

| Windows 版 | macOS 版 |
|---|---|
| `ctypes.windll` 检测管理员 | `os.geteuid() == 0` |
| `shutil.disk_usage("C:\\")` | `os.statvfs("/")` |
| `TEMP` / `USERPROFILE` / `AppData` 路径 | `Path.home()` + `~/Library/...` |
| `encoding='gbk'` | `encoding='utf-8'` |
| Windows 专有目标（Prefetch, WER, Edge/Chrome Cache v1） | macOS 等价目标 |
| Listbox + curselection | Canvas+Frame 滚动列表 + Checkbutton var |

## macOS 清理目标（共 15 项）

- **系统**: ~/Library/Caches, 废纸篓 ~/.Trash
- **开发**: Xcode DerivedData, CoreSimulator, npm _cacache, pip 缓存
- **浏览器**: Safari, Chrome, Edge, Firefox 缓存
- **日志**: ~/Library/Logs, /var/log（标记 ⚠️ 需要管理员）
- **容器**: Docker 数据（可选）
- **文件**: ~/Downloads（可选）
- **系统**: Homebrew 缓存 ~/Library/Caches/Homebrew

## GUI 功能

1. 顶部磁盘信息卡片（总容量 / 已使用 / 可用空间 / 可清理）
2. 进度条显示磁盘使用率
3. 分类筛选按钮（全部/系统/开发/浏览器/日志/容器/文件）
4. Canvas 滚动列表，每行含 Checkbutton + 彩色类别标签 + 名称 + 大小
5. ⚠️ 标签自动标注需要管理员的项目（黄色警告文字）
6. ⭐ 标签标注可选项目
7. Scan / 清理选中 / 全选 / 取消全选按钮
8. 底部日志输出窗口（彩色日志）
9. 清理完成后重新读取磁盘信息

## 安全设计

- sudo 目标（/var/log）默认勾选但清理前会弹出警告对话框
- 非 sudo 用户尝试清理 sudo 项目时弹窗询问是否跳过
- 所有文件删除使用 `shutil.rmtree(ignore_errors=True)`，权限错误静默跳过并记录
