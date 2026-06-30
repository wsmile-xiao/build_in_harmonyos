# UPower

## 简介

UPower 是一个抽象层，用于枚举电源设备、监听设备事件、查询历史和统计数据。

它是 freedesktop.org 项目的一部分，为桌面环境提供统一的电源管理接口。

## 版本

- **0.99.20** (2026-05-28 编译)

## 功能

- 枚举系统中的所有电源设备（电池、UPS、交流电源等）
- 监听电源设备状态变化事件
- 查询电池历史和统计信息
- 提供显示设备（合成设备）用于显示电池状态
- 支持笔记本盖子状态检测

## 组件

| 组件 | 说明 | 状态 |
|------|------|------|
| `upower` | 命令行工具 | ✅ PASS |
| `upowerd` | 守护进程 | ⚠️ 需 D-Bus |
| `libupower-glib` | GLib 客户端库 | ✅ PASS |

## API

libupower-glib 提供 C API，主要函数：

- `up_client_new()` - 创建客户端
- `up_client_get_devices()` - 获取设备列表
- `up_client_get_on_battery()` - 检查是否使用电池
- `up_device_new()` - 创建设备对象
- `up_device_refresh_sync()` - 刷新设备信息

## 使用示例

### 命令行

```bash
# 列出所有电源设备
upower -e

# 显示详细信息
upower -d

# 监控电源事件
upower -m
```

### C API

```c
#include <libupower-glib/upower.h>

UpClient *client = up_client_new();
GPtrArray *devices = up_client_get_devices(client);

for (guint i = 0; i < devices->len; i++) {
    UpDevice *device = g_ptr_array_index(devices, i);
    g_print("Device: %s\n", up_device_get_object_path(device));
}
```

## 系统要求

### 运行时

- D-Bus 系统服务（守护进程运行必需）
- udev 设备管理器
- `/sys/class/power_supply` 目录（Linux 内核电源设备抽象）

### HarmonyOS 注意事项

当前 HarmonyOS 系统限制：
- D-Bus 服务可能未完整运行
- `/sys/class/power_supply` 目录不存在
- 守护进程需要系统级服务支持才能完整运行

**命令行工具和库 API 可正常使用**，守护进程功能受限。

## 安装

预编译包包含：
- `bin/upower`
- `libexec/upowerd`
- `lib/libupower-glib.so.*`
- `include/libupower-glib/*.h`
- `lib/external/` (依赖库)

## 许可证

GPLv2+

## 来源

- 官方网站: https://upower.freedesktop.org/
- 源代码: https://gitlab.freedesktop.org/upower/upower

## 编译信息

- 构建系统: meson + ninja
- 编译器: clang 15.0.4
- 编译日期: 2026-05-28
- 测试状态: PASS (核心功能)