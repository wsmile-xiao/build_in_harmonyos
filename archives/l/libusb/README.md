# libusb

## 简介

libusb 是一个跨平台的 USB 设备访问库，提供通用的 API 用于 USB 设备枚举、配置和通信。本归档为 libusb 1.0.27 在鸿蒙 (HarmonyOS) 平台的预编译版本。

> **重要提示**: libusb 在鸿蒙普通应用沙箱中**可以编译链接和初始化，但无法完成实际的 USB 设备通信**。鸿蒙 SELinux 安全策略从设备枚举到 I/O 控制全链路阻断了 USB 硬件访问。详见下方[能力评估](#能力评估)。

## 基本信息

| 项目 | 值 |
|------|-----|
| 版本 | 1.0.27 |
| 构建系统 | autotools |
| 许可证 | LGPL-2.1 |
| 主页 | https://libusb.info/ |
| 架构 | aarch64 (ARM64) |
| 动态依赖 | 仅 libc.so（零外部依赖） |
| 编译日期 | 2026-06-24 |

## 能力评估

### 能做什么 ✅

以下能力已在鸿蒙平台验证通过（测试日期 2026-06-24）：

| 能力 | 验证结果 | 说明 |
|------|---------|------|
| 编译链接 | ✅ 通过 | 动态链接和静态链接均可正常编译 |
| 库初始化 | ✅ 通过 | 需配合 `NO_DEVICE_DISCOVERY` 选项 |
| 版本查询 | ✅ 通过 | `libusb_get_version()` 正确返回 1.0.27 |
| 能力查询 | ✅ 通过 | `libusb_has_capability()` 报告支持热插拔/HID/驱动分离 |
| 选项设置 | ✅ 通过 | `libusb_set_option()` 日志级别等正常 |
| 错误处理 | ✅ 通过 | `libusb_error_name()` / `libusb_strerror()` 正常 |
| 内存稳定性 | ✅ 通过 | 30 次初始化/销毁循环无泄露 |
| pkg-config 集成 | ✅ 通过 | `pkg-config --cflags --libs libusb-1.0` 输出正确 |

### 不能做什么 ❌

以下能力在鸿蒙普通应用沙箱（`hishell_hap` 域）中**不可用**：

| 能力 | 状态 | 阻塞原因 | 可否修复 |
|------|------|---------|---------|
| USB 设备枚举 | ❌ 阻断 | sysfs `/sys/bus/usb/devices/` 不可访问（缺 `dir read open` 权限） | 需 SELinux 策略补充 |
| 打开 USB 设备 | ❌ 阻断 | `/dev/bus/usb/` 设备文件不可访问（缺 `dir search` 权限） | 需 SELinux 策略补充 |
| USB I/O 读写 | ❌ 阻断 | `neverallowx hap_domain dev_bus_usb_file (ioctl chr_file ...)` 硬性禁止 | ❌ 不可修复（neverallow） |
| 设备控制传输 | ❌ 阻断 | 同上，`USBDEVFS_*` ioctl 全部被 neverallow 拦截 | ❌ 不可修复（neverallow） |
| 热插拔事件监听 | ❌ 阻断 | `neverallow hap_domain domain (netlink_kobject_uevent_socket ...)` 硬性禁止 | ❌ 不可修复（neverallow） |

### 根本原因

libusb 的 USB 通信链路需要 5 个环节全部打通，鸿蒙在 ②③④⑤ 四个环节设置了 SELinux 阻断：

```
① 库初始化 → ② 设备枚举 → ③ 打开设备 → ④ ioctl 控制 → ⑤ USB I/O
   ✅ 通过      ❌ sysfs      ❌ 设备文件    ❌ neverallow     ❌ neverallow
                权限缺失       权限缺失       hap_domain禁     hap_domain禁
```

其中 ②③ 是**目录权限缺失**（可通过 SELinux allow 规则补充修复），④⑤ 是 **neverallow 硬性禁止**（编译时约束，无法通过 allow 规则覆盖）。

> **结论**: 即使修复 ②③ 的目录权限，④⑤ 的 neverallow 仍然阻断 USB I/O。在普通应用沙箱中，libusb **无法完成任何实际的 USB 硬件操作**。

## 建议

### 场景 1: 普通应用需要 USB 通信

**推荐方案**: 使用鸿蒙原生 USB API，不要用 libusb。

```typescript
// 使用 @ohos.usbManager（ArkTS/JS）
import usbManager from '@ohos.usbManager';

// 获取设备列表
const devices = usbManager.getDevices();

// 打开设备
const pipe = usbManager.connectDevice(device);

// 读写数据
usbManager.bulkTransfer(pipe, endpoint, buffer, timeout);
```

**原因**: `@ohos.usbManager` 通过系统 USB 服务的 binder IPC 调用，不受应用沙箱 SELinux 限制。libusb 直接访问 `/dev/bus/usb/` 和 sysfs，被 SELinux 阻断。

### 场景 2: C/C++ 底层组件需要跨平台 USB 支持

**推荐方案**: 以 `usb_host` 或 `usb_service` SELinux 域运行。

将编译好的程序部署为系统服务，配置对应的 SELinux 域。`usb_host` 域有 USB 设备文件的完整访问权限（包括 ioctl）。

适用场景：SANE 扫描仪服务、打印驱动、USB 串口工具等系统级组件。

### 场景 3: 需要将依赖 libusb 的第三方软件移植到鸿蒙

**推荐方案**: 评估是否能以系统服务运行。

1. 软件能以系统服务（非 HAP 应用）运行 → 编译 libusb，配置 `usb_host` 域，正常使用
2. 软件必须在应用沙箱中运行 → 需要 USB 功能的部分改用 `@ohos.usbManager` API 重写，libusb 仅用于非硬件操作（如数据结构定义、错误码处理）

### 场景 4: 需要热插拔事件通知

**推荐方案**: 轮询代替事件驱动。

netlink `neverallow` 是硬限制，无法绕过。应用可通过定期调用 `libusb_get_device_list()`（需 SELinux 权限）或 `@ohos.usbManager` 的 `on('deviceAttached'/'deviceDetached')` 监听设备变化。

## 安装

```bash
# 通过 cmd-pkgs 公共安装脚本
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libusb 1.0.27

# 或从预编译包手动安装
tar xzf libusb-1.0.27-ohos-aarch64.tar.gz -C /
```

## 编译链接

```bash
# 动态链接
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
clang -o myapp myapp.c $(pkg-config --cflags --libs libusb-1.0)

# 静态链接
clang -static -o myapp myapp.c \
    -I$HOME/usr/local/include/libusb-1.0 \
    $HOME/usr/local/lib/libusb-1.0.a \
    -lpthread
```

## 初始化代码（系统服务场景）

以 `usb_host` 域运行的系统服务可直接使用标准初始化：

```c
#include <libusb.h>

libusb_context *ctx;
int ret = libusb_init_context(&ctx, NULL, 0);  // 标准初始化
if (ret != 0) {
    fprintf(stderr, "libusb 初始化失败: %s\n", libusb_strerror(ret));
    return -1;
}

/* 枚举设备（需 usb_host SELinux 域） */
libusb_device **devs;
ssize_t cnt = libusb_get_device_list(ctx, &devs);
printf("发现 %zd 个 USB 设备\n", cnt);

/* 正常进行 USB I/O ... */

libusb_free_device_list(devs, 1);
libusb_exit(ctx);
```

应用沙箱场景需使用 `NO_DEVICE_DISCOVERY` 选项（仅初始化，无设备访问）：

```c
struct libusb_init_option opts[1];
opts[0].option = LIBUSB_OPTION_NO_DEVICE_DISCOVERY;
libusb_init_context(&ctx, opts, 1);  // 跳过设备枚举，初始化成功
// 但后续 get_device_list 返回 0 设备，无法进行 USB I/O
```

## 产物清单

| 文件 | 大小 | 说明 |
|------|------|------|
| libusb-1.0.so.0.4.0 | 141KB | 共享库（SONAME: libusb-1.0.so.0） |
| libusb-1.0.a | 235KB | 静态库 |
| libusb.h | 82KB | 头文件 |
| libusb-1.0.pc | — | pkg-config 文件 |

预编译包: `libusb-1.0.27-ohos-aarch64.tar.gz` (806KB)

## 补丁列表

| 补丁 | 文件 | 说明 |
|------|------|------|
| 0001-configure.patch | configure | HMDFS 文件系统 umask 077 导致临时目录权限异常 |
| 0002-libusb-os-linux_netlink.c.patch | linux_netlink.c | E091: sockaddr_storage 重定义冲突（`#ifdef __OHOS__` define-guard） |
| 0003-libusb-os-linux_usbfs.c.patch | linux_usbfs.c | 鸿蒙内核版本解析失败（`HongMeng Kernel X.Y.Z` 格式兼容） |

## SELinux 权限分析

> 以下为 SELinux 策略详细分析，供系统开发者参考。

### sysfs USB 设备访问

当前应用域: `u:r:hishell_hap:s0`

| 路径 | SELinux 标签 | 已有权限 | 缺失权限 |
|------|-------------|---------|---------|
| `/sys/bus/` | `sysfs` | 无 | `dir (search)` |
| `/sys/bus/usb/` | `sysfs` | 无 | `dir (search)` |
| `/sys/bus/usb/devices/` | `dev_bus_usb_file` | `dir (search)` | `dir (read open)` |
| `/sys/bus/usb/devices/*` | `dev_bus_usb_file` | `file (read getattr open)` | — |
| `/dev/bus/usb/` | `dev_bus_usb_file` | 无 | `dir (search read open)` |

策略补充方案（仅修复枚举，不解决 I/O）：
```cil
(allow hishell_hap sysfs (dir (search)))
(allow hishell_hap dev_bus_usb_file (dir (read open search)))
```

### USB 设备 I/O 控制（不可修复）

```cil
# neverallow 硬性禁止 — 编译时约束，无法覆盖
(neverallowx hap_domain dev_bus_usb_file (ioctl chr_file ((range 0x0 0x54ff) ...)))
(neverallowx hap_domain dev_bus_usb_file (ioctl chr_file ((range 0x5501 0x5503) ...)))
```

### Netlink 热插拔（不可修复）

```cil
# neverallow 硬性禁止 HAP 域使用 netlink kobject_uevent socket
(neverallow hap_domain domain (netlink_kobject_uevent_socket (write append)))
```

可使用 netlink kobject_uevent 的域: `init`、`udevd`、`hdf_ext_devmgr`、`audio_server`、`multimodalinput`、`charger`、`sane_service`、`scan_service`

## 功能测试

完整测试报告: [reports/functional-test-report.md](1.0.27/reports/functional-test-report.md)

| 测试模式 | 通过 | 失败 | 通过率 |
|----------|------|------|--------|
| 默认模式 | 4/13 | 4 | 30.8% |
| NO_DEVICE_DISCOVERY | 7/8 | 1 | 87.5% |

## 依赖

无外部库依赖。仅依赖系统 libc.so。

## 参考

- [libusb 官方文档](https://libusb.sourceforge.io/api-1.0/)
- [libusb 源码](https://github.com/libusb/libusb)
- [鸿蒙 SELinux 策略](https://gitee.com/openharmony/security_selinux)
- [鸿蒙 USB Manager API](https://gitee.com/openharmony/usb_usb_manager)
