# libftdi

> 通过 libusb 0.1 API 访问 FTDI USB 转接芯片（FT232/FT245 等）的驱动库。

## 简介

libftdi 提供 FTDI USB 桥接芯片的高层操作：打开/关闭设备、设置波特率与数据位、
位操作（bitbang）、EEPROM 读写与设备枚举。它建立在 libusb 0.1 API 之上
（本仓库用 `libusb-compat/0.1.7` 提供该兼容层），公共头 `ftdi.h` 自身
`#include <usb.h>`。

## OHOS 适配要点

- **选用上游 CMake 构建**（tarball 同时带 autotools 与 CMake）。autotools 路径在 OHOS
  上需要三处绕行：① `configure` 硬依赖 `libusb-config` 工具，而 `libusb-compat/0.1.7`
  制品包不提供该脚本；② native 模式下 configure 运行 conftest 失败
  （`AutotoolsDeps` 把 `-lusb/-lusb-1.0` 放进 `LIBS`，conftest 运行时找不到
  `libusb-1.0.so.0`）；③ 内置 libtool 2.2.6 在本环境会写死 ksh 的
  `ECHO="print -r --"`（bash 下 `print: command not found`）并使
  `old_archive_cmds` 丢转义（空归档名）。CMake 路径不经过 libtool，也不做运行探测。
- `FindUSB.cmake` 用显式缓存变量短路：`LIBUSB_INCLUDE_DIR=<libusb-compat>/include`、
  `LIBUSB_LIBRARIES=<libusb-compat>/lib/libusb.a;<libusb>/lib/libusb-1.0.so`
  （依赖包内 `.pc` 记录的是发布机路径，不可直接用）。
- `ftdi.h` 公开 `#include <usb.h>` → `libusb-compat` 以
  `transitive_headers/transitive_libs` 传播给消费者。
- 安装目录：补丁固定 `LIB_SUFFIX` 为空（上游对 64 位装到 `lib64/`），与 Conan `lib/` 一致。
- 现代 CMake 兼容：`-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（上游声明 `cmake_minimum_required(2.6)`），
  并用补丁修正 `examples/CMakeLists.txt` 把 `include()` 当 `include_directories()` 用的笔误。
- 关闭 doxygen（`DOCUMENTATION=OFF`）、C++ 包装（`FTDIPP=OFF`，需 boost）与 python 绑定；
  示例程序保持构建，`examples/find_all` 在真机运行作为上游证据。
- 产物：`lib/libftdi.so.1.20.0`（upstream CMake 设 `SOVERSION 1`）、`lib/libftdi.a`、
  `include/ftdi.h`、`lib/pkgconfig/libftdi.pc`；`bin/libftdi-config` 帮助脚本已删除。

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| libusb-compat | 0.1.7 | 提供 `usb.h`、`libusb.a` 与 libusb 0.1 兼容层（底层为 libusb/1.0.27） |

## 使用

```cmake
find_package(libftdi CONFIG REQUIRED)
target_link_libraries(app PRIVATE libftdi::libftdi)
```

pkg-config：

```sh
pkg-config --cflags --libs libftdi
```

```c
#include <ftdi.h>

struct ftdi_context ctx;
ftdi_init(&ctx);
struct ftdi_device_list *devices = NULL;
int count = ftdi_usb_find_all(&ctx, &devices, 0x0403, 0x6001); /* FTDI 默认 VID/PID */
ftdi_list_free(&devices);
ftdi_deinit(&ctx);
```

## 功能验证

```sh
conan create archives/l/libftdi/0.20 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# 上游 examples/find_all 1/1 exit 0（无硬件时报 0 台）；消费者 7/7 断言通过
```

---

## 1.5 适配说明

### 简介

libFTDI 是一个开源库，用于与 FTDI 芯片（FT232、FT245、FT2232、FT4232、FT232H、FT230X 系列）通信。它基于 libusb 在用户空间完成 USB 通信，无需内核侧驱动。本归档为 libftdi1 1.5 在鸿蒙 PC (OHOS aarch64) 的 Conan 归档。

### 支持的芯片

- FT8U232AM / FT8U245AM (TYPE_AM)
- FT232BM / FT245BM 及 BL/BQ 变种 (TYPE_BM)
- FT2232C / FT2232L / FT2232D (TYPE_2232C)
- FT232R / FT245R (TYPE_R)
- FT2232H / FT4232H (TYPE_2232H / TYPE_4232H)
- FT232H (TYPE_232H)
- FT230X / FT231X / FT234XD (TYPE_230X)

### 版本

| 版本 | 状态 | 编译日期 | 补丁数 | 产物 |
|------|------|----------|--------|------|
| 1.5 | built | 2026-09-17 | 1 | libftdi1.so.2.5.0 (shared) / libftdi1.a (static) |

### 依赖

- **libusb/1.0.27** (ohpcd, 含 OHOS 内核补丁)：USB 设备通信，构建与运行时依赖
- **libconfuse**：ftdi_eeprom 工具需要 —— 仓库无可用包，构建已禁用 ftdi_eeprom，仅构建核心库

### 环境约束（重要）

OHOS PC 应用沙箱无 USB 子系统访问权限（SELinux），`libusb_init(NULL)` 返回 -1
(LIBUSB_ERROR_IO)。因此：

- ✅ 库可正常编译、链接、安装（shared / static 两种变体均通过 conan create 全流程）
- ✅ 纯计算 API（`ftdi_convert_baudrate`）、版本查询（`ftdi_get_library_version`）、
  错误处理（`ftdi_get_error_string`）、NULL 安全路径全部可用
- ❌ `ftdi_new()` / `ftdi_init()` 及一切真实 USB 操作不可离线运行（需 `usb_host` SELinux 域或系统服务场景）

与底层 libusb 的能力边界一致，详见 `archives/l/libusb/README.md`。

### 消费方式

```cmake
find_package(libftdi1 REQUIRED)   # CMakeDeps 生成的模块名
target_link_libraries(app PRIVATE libftdi1::libftdi1)
```

头文件路径：`<libftdi1/ftdi.h>`（注意 `ftdi.h` 内部 `#include <libusb.h>`，
包已通过 `cpp_info.requires` 传递 libusb 头文件路径，无需手工额外配置）。

### 补丁

| 补丁 | 说明 |
|------|------|
| 0001-cmake-harmonyos-libdir.patch | ① CMake 无 Platform/HarmonyOS 模块 → UNIX 变量未定义 → libdir/LIBFTDI_LIBRARY_DIRS 为空 → configure_package_config_file 失败：增加 HarmonyOS 显式判断；② 上游硬编码 add_library(ftdi1 SHARED)：新增 DONT_BUILD_SHARED 开关使 static-only 构建产出 libftdi1.a |

### 测试

- **上游离线测试**：test/baudrate.cpp 的官方波特率测试向量 **284 条**（8 种芯片类型）
  经 `convert_baudrate_UT_export`（上游单测导出包装）全部通过，断言语义与上游
  calc_result 四元组一致（actual_baudrate / divisor / fractional_bits / clock）。
- **上游硬件依赖测试**：test/basic.cpp、test/baudrate.cpp 原始 fixture（`ftdi_new` →
  `libusb_init`，沙箱必败），如实归类为 hardware-environment，不计入通过。
- **OHOS 专项**：ELF64 AArch64 自检、SONAME (libftdi1.so.2)、NEEDED 依赖闭包
  （libusb-1.0.so.0 + libc.so）、无路径泄漏、RPATH/RUNPATH 审计。
- 运行方式：test_package/conanfile.py `test()` 中 `self.run()` 真实执行消费者二进制。

### 许可证

LGPL-2.1-or-later（核心库 src/，见包内 licenses/COPYING.LIB）。
ftdi_eeprom 工具为 GPL-2.0-or-later，本归档未构建该组件。
