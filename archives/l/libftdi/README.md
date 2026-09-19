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
