# conky

## 简介
conky 是一个轻量级的系统监视器，可以在桌面显示 CPU、内存、磁盘、网络等系统信息。它高度可配置，支持多种显示方式。

## 功能
- 显示 CPU、内存、磁盘使用率
- 显示网络流量和连接状态
- 显示进程信息
- 支持 Lua 脚本扩展
- 高度可配置的显示样式

## 版本
- **1.19.0** (2026-05-26) - 编译成功，禁用 X11/Wayland/I18N

## 依赖
- Lua 5.3.6（必需）
- ncursesw 6.4（必需）

## 平台适配说明
- cmake 条件编译缺失：需应用补丁 0001-fix-cmake-conditional-compilation.patch
- getutline 函数缺失：需应用补丁 0002-fix-getutline-missing.patch
- X11/Wayland 初始化缺失：需应用补丁 0003-fix-x11-wayland-init.patch
- 建议禁用 X11/Wayland/I18N 功能

## 使用
```bash
# 安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- conky 1.19.0

# 验证
conky --version

# 运行
conky -c /path/to/config
```