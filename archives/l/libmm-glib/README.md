# libmm-glib

## 简介

libmm-glib 是 ModemManager 的 GLib 库接口，提供移动宽带 modem 的管理和控制功能。

## 功能

- **libmm-glib 库**：GLib 封装库，提供 modem 管理的客户端 API
- **mmcli 命令行工具**：ModemManager 的命令行客户端
- **ModemManager daemon**：modem 管理守护进程（❌ 鸿蒙上编译失败）

## 依赖

- glib 2.88.0
- dbus 1.14.10
- gio-unix-2.0 2.88.0

## 鸿蒙适配状态

### 已成功编译的版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.20.0 | published | libmm-glib 库可用 |
| 1.24.2 | published | libmm-glib 库可用，mmcli 命令行工具可用 |

### 适配要点

1. **构建系统**：meson（需要禁用 systemd/polkit/udev）
2. **头文件冲突**：鸿蒙 SDK 的 linux/socket.h 和 sys/socket.h 都定义 sockaddr_storage，导致 daemon 编译失败
3. **功能限制**：ModemManager daemon 不可用，只能使用客户端库

### 使用限制

- ❌ ModemManager daemon 编译失败（头文件冲突）
- ✅ libmm-glib.so 库可用（客户端应用可使用）
- ✅ mmcli 命令行工具可用
- ⚠️ 需要手动处理 ModemManager 功能的替代方案

## 安装

```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libmm-glib 1.24.2
```

## 参考链接

- [ModemManager 官网](https://www.freedesktop.org/wiki/Software/ModemManager/)
- [libmm-glib API 文档](https://www.freedesktop.org/software/ModemManager/api/latest/)