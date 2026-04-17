# C盘空间清理工具 (C Drive Cleaner)

一个安全、高效的 Windows C盘空间清理工具，帮助你释放磁盘空间。

## ✨ 功能特性

- 🔍 **智能扫描** - 自动扫描可清理的文件和缓存
- 🧹 **安全清理** - 只清理临时文件、缓存等无用文件，不删除系统文件
- 📊 **清理报告** - 详细显示清理结果和磁盘状态
- ⚡ **快速高效** - 快速释放磁盘空间

## 🗑️ 清理范围

| 清理项目 | 说明 |
|---------|------|
| Windows 临时文件 | `%TEMP%` 目录下的临时文件 |
| 系统临时文件 | `C:\Windows\Temp` |
| 用户临时文件 | `AppData\Local\Temp` |
| 缩略图缓存 | Windows 资源管理器缩略图 |
| Windows 更新缓存 | 已安装更新的下载缓存 |
| 预取文件 | Windows Prefetch 文件 |
| 错误报告文件 | Windows 错误报告 |
| 浏览器缓存 | Edge / Chrome 缓存 |

## 🚀 使用方法

### 方式1：直接运行 Python 脚本
```bash
python cleaner.py
```

### 方式2：运行 EXE（无需安装 Python）
```bash
dist\C盘清理工具.exe
```

## 📦 安装依赖

```bash
pip install -r requirements.txt
```

## ⚠️ 注意事项

- 本工具**只清理临时文件和缓存**，不会删除个人文件
- 建议以**管理员身份**运行以获得最佳清理效果
- 清理前会显示扫描结果，需要用户确认后才会执行

## 📄 许可证

MIT License
