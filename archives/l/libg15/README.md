# libg15

## 简介

libg15 是罗技 G11/G15（及 G510/G13 等）键盘的 C 语言用户态驱动库，提供 LCD 显示、扩展按键读取、LED/背光控制等 API。本归档为 libg15 1.3.0-svn324 在鸿蒙 (HarmonyOS) 平台的预编译版本。

> **重要提示**: libg15 依赖 libusb-1.0。鸿蒙应用沙箱对 USB 硬件访问有 SELinux 硬性限制（详见 [libusb 归档](../libusb/README.md)），因此 libg15 在无 G15 键盘的鸿蒙设备上**编译链接和初始化可用，但实际 USB 硬件操作不可用**（`initLibG15()` 返回 `G15_ERROR_OPENING_USB_DEVICE`）。

## 基本信息

| 项目 | 值 |
|------|-----|
| 版本 | 1.3.0-svn324（上游 1.3.0~svn324，Debian 写法） |
| 构建系统 | autotools |
| 许可证 | GPL-2.0-or-later |
| 主页 | https://salsa.debian.org/debian/libg15 |
| 架构 | aarch64 (ARM64) |
| 编译依赖 | libusb/1.0.27（制品仓已发布） |
| 编译日期 | 2026-09-21 |

## 能力评估

| 能力 | 验证结果 | 说明 |
|------|---------|------|
| 编译链接 | ✅ 通过 | 动态（libg15.so）+ 静态（libg15.a）均可用 |
| 库初始化 | ✅ 通过 | `initLibG15()` 初始化 libusb-1.0 上下文并枚举设备 |
| 版本常量 | ✅ 通过 | `LIBG15_VERSION` = 1201 |
| 无硬件返回码 | ✅ 通过 | 无 G15 键盘时 `initLibG15()` 返回 `G15_ERROR_OPENING_USB_DEVICE`（预期） |
| LCD/按键/LED 硬件操作 | ❌ 无硬件 | 需真实 G15/G11 键盘；且鸿蒙沙箱 USB I/O 被 SELinux 阻断 |

## 编译链接

```bash
# 动态链接（经 Conan 拉取依赖）
conan install libg15/1.3.0-svn324@ohpcd/stable
clang -o myapp myapp.c -I<prefix>/include -L<prefix>/lib -lg15

# 静态链接
clang -o myapp myapp.c -I<prefix>/include <prefix>/lib/libg15.a -lusb-1.0 -lpthread
```

## 初始化代码（无硬件场景）

```c
#include <libg15.h>

int r = initLibG15();
if (r == G15_NO_ERROR) {
    /* 检测到 G15 键盘 */
} else if (r == G15_ERROR_OPENING_USB_DEVICE) {
    /* 无硬件或权限不足 —— 鸿蒙无 G15 时的预期返回 */
}
```

## 产物清单

| 文件 | 说明 |
|------|------|
| libg15.so.1.0.1 (+ .so/.so.1) | 共享库（SONAME: libg15.so.1），OHOS 已签名 |
| libg15.a | 静态库 |
| libg15.h | 公共头文件 |

## 补丁列表

| 补丁 | 文件 | 说明 |
|------|------|------|
| 0001-configure.in.patch | configure.in | libusb-0.1 → libusb-1.0（AC_CHECK_LIB usb-1.0、头文件 libusb-1.0/libusb.h）（源自 Debian 官方补丁，按文件拆分重命名） |
| 0002-libg15.c.patch | libg15.c | libusb-1.0 API 全量迁移 + 拼写修正（源自 Debian 官方补丁 01/02，按文件拆分重命名） |

配方内另有非补丁适配：bootstrap 生成 configure 后改写 `umask 077`→`umask 022`（HMDFS 临时目录可写，libusb 配方同款）；bootstrap 前导出 `AUTOM4TE`。

## 上游测试（R51）

上游无测试套件：`Makefile.am` 无 `TESTS`/`check_PROGRAMS`，`make check` 为空 no-op（清点证据见 [1.3.0-svn324/notes.md](1.3.0-svn324/notes.md)）。验证由 test_package 承担（link + `initLibG15()` 返回码 + `LIBG15_VERSION` + `g15DeviceCapabilities()`）。

## 依赖

| 包 | 版本 | 来源 |
|----|------|------|
| libusb | 1.0.27 | 制品仓 ohpcd（已发布） |

## 参考

- [Debian libg15 源码](https://salsa.debian.org/debian/libg15)
- [g15tools（上游项目）](https://g15tools.sourceforge.net/)
- [libusb 鸿蒙能力评估](../libusb/README.md)
