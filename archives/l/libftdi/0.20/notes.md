# libftdi 0.20 适配笔记

## 编译环境
- 构建系统: **上游 CMake**（tarball 同时带 autotools 与 CMake，本仓库选用 CMake，理由见下）
- 编译日期: 2026-09-18
- 编译器: OHOS clang（Conan profile `ohos-aarch64`）
- 依赖: `libusb-compat/0.1.7`（提供 `usb.h` + `libusb.a`；底层 `libusb/1.0.27`）
- CMake 选项: `DOCUMENTATION=OFF`、`FTDIPP=OFF`、`PYTHON_BINDINGS=OFF`、`EXAMPLES=ON`
- 状态: built

## 版本与源码
- 任务版本 `0.20` == Debian `libftdi_0.20.orig.tar.gz`（上游 0.20 发布版）
- sha256 `3176d5b5986438f33f5208e690a8bfe90941be501cc0a72118ce3d338d4b838e`

## 为什么用 CMake 而不是 autotools

上游 tarball 两套构建系统都可用。autotools 路径在 OHOS 上需要三处绕行，而 CMake 路径不需要：

| # | autotools 路径的问题 | CMake 路径 |
|---|----------------------|-----------|
| 1 | `configure.in` 用 `AC_CHECK_TOOL(HAVELIBUSB, libusb-config)` 并调用 `--cflags/--libs/--version`，而制品仓 `libusb-compat/0.1.7` 包**不含** `libusb-config` ⇒ 必须自写最小 shim（并处理 `AC_CHECK_TOOL` 在交叉模式查找 `<host>-` 前缀名） | `FindUSB.cmake` 用 **pkg-config `libusb`**；本配方直接用 `LIBUSB_INCLUDE_DIR`/`LIBUSB_LIBRARIES` 缓存变量短路，连 pkg-config 都不需要 |
| 2 | native 模式下 configure 会运行 conftest，而 `AutotoolsDeps` 把 `-lusb -lusb-1.0` 放进 `LIBS`，conftest 动态依赖 `libusb-1.0.so.0`（configure 阶段不在加载路径）⇒ `cannot run C compiled programs` | CMake 交叉编译不做运行探测 |
| 3 | libtool 2.2.6 + 本环境：生成脚本把 ksh 的 `ECHO="print -r --"` 写死（bash 下 `print: command not found`）；且 `old_archive_cmds` 丢转义 ⇒ `llvm-ar: error: an archive name must be specified` | 不经过 libtool |

> 上述三点都在本 PR 的知识草稿中记录（含最小 shim、`AC_CHECK_TOOL` 前缀、libtool ECHO/转义三项的定位与修法），
> 它们是"老 autotools 工程在 OHOS 上常见坑"的一手证据；对只有 autotools 的工程仍然适用。

## 产物
- `lib/libftdi.so.1.20.0`（upstream CMake 设 `SOVERSION 1`）+ 软链、`lib/libftdi.a`
- `include/ftdi.h`
- `lib/pkgconfig/libftdi.pc`
- `licenses/COPYING.LIB`
- **已删除**：`bin/libftdi-config`（帮助脚本）；示例程序只构建不安装

## 关键点

- `LIBUSB_LIBRARIES` 由配方从依赖解析：`<libusb-compat>/lib/libusb.a;<libusb>/lib/libusb-1.0.so`
  （libusb 0.1 兼容层是静态库，其符号引用 libusb-1.0）。
- `FindUSB.cmake` 默认走 pkg-config，但 libusb/libusb-compat 包内 `.pc` 记录的是发布机
  路径（`libusb.pc` 的 `prefix` 指向构建缓存目录、`libusb-1.0.pc` 是 `/usr/local`），
  因此用缓存变量短路更可靠。
- `ftdi.h` 公开 `#include <usb.h>`：`libusb-compat` 以
  `transitive_headers=True, transitive_libs=True` + `cpp_info.requires` 传播给消费者。
- `libftdi.pc`：上游 CMake 用 `CMAKE_INSTALL_PREFIX` 生成（Conan 已指向包目录），
  仅需把 `exec_prefix` 从 `.../bin` 归一化。
- **安装目录**（补丁）：上游对 64 位目标强制 `LIB_SUFFIX=64`，会装到 `lib64/`（Conan 的
  `cpp_info.libdirs` 是 `lib/`）→ `patches/0002-cmake-lib-suffix.patch` 固定为空。
- **现代 CMake 兼容**（补丁）：上游声明 `cmake_minimum_required(VERSION 2.6)`（CMake 4 拒绝，
  用 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`）；`examples/CMakeLists.txt` 把 `include()` 当
  `include_directories()` 用（2011 年的笔误）→ `patches/0001-examples-include-directories.patch`。

## 上游行为要点（消费者测试依据）

- `ftdi_usb_find_all()` 在**无设备**时返回 `0`（不是错误）。
- `ftdi_get_error_string()` 对 `NULL` 上下文返回 `""`。
- `ftdi_usb_open()` 找不到设备时返回负值并把错误写入 `error_str`，且 `usb_dev` 保持 `NULL`。
- `ftdi_list_free()` 会把传入的指针置 `NULL`。
- 上游无 `make check`；`examples/find_all`（`noinst`/CMake target）在无硬件时打印
  `Number of FTDI devices found: 0` 并 exit 0，用作真机上游证据。

## 验证结果

```sh
conan create archives/l/libftdi/0.20 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# rc=0
# 上游：examples/find_all -> exit 0（Number of FTDI devices found: 0）
# 消费者：ctest + ./libftdi_consumer -> 7/7 断言通过
```
