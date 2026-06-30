# libmodbus 3.1.12 — OpenHarmony/HarmonyOS Pre-compiled Package

## Overview

libmodbus 是一个用于发送/接收 Modbus 数据的 C 语言库，支持 Modbus TCP 和 RTU (串口) 协议。

- **版本**: 3.1.12
- **平台**: OpenHarmony / HarmonyOS aarch64
- **构建系统**: autotools (configure.ac + Makefile.am)
- **编译器**: clang-15 / clang++-15
- **构建日期**: 2026-05-21

## 包内容

| 文件路径 | 说明 |
|---------|------|
| `include/modbus/modbus.h` | 主 API 头文件 (13123 bytes) |
| `include/modbus/modbus-version.h` | 版本宏定义 (2205 bytes) |
| `include/modbus/modbus-rtu.h` | RTU (串口) API (1195 bytes) |
| `include/modbus/modbus-tcp.h` | TCP API (1360 bytes) |
| `lib/libmodbus.so.5.1.0` | 共享库本体 (63872 bytes) |
| `lib/libmodbus.so.5` → `libmodbus.so.5.1.0` | SONAME symlink |
| `lib/libmodbus.so` → `libmodbus.so.5` | 开发 symlink |
| `lib/libmodbus.la` | libtool 档案 |
| `lib/pkgconfig/libmodbus.pc` | pkg-config 文件 |
| `share/doc/libmodbus/` | 文档 (AUTHORS, NEWS.md, README.md) |

## 使用方法

### pkg-config 编译

```bash
export PKG_CONFIG_PATH=/path/to/lib/pkgconfig:$PKG_CONFIG_PATH

# 编译（注意: cflags 给出的是 modbus/ 子目录路径，使用 #include <modbus.h>）
clang $(pkg-config --cflags libmodbus) \
      $(pkg-config --libs libmodbus) \
      -o my_app my_app.c
```

### 头文件引用

```c
#include <modbus.h>        // 主 API
#include <modbus-version.h> // 版本宏
#include <modbus-rtu.h>    // RTU 串口 API
#include <modbus-tcp.h>    // TCP API
```

### 版本检测

```c
printf("libmodbus %s\n", LIBMODBUS_VERSION_STRING);  // 输出 "3.1.12"
```

```bash
pkg-config --modversion libmodbus  # 输出 3.1.12
```

## 构建补丁说明

| 补丁 | 类型 | 说明 |
|------|------|------|
| 0001-build-aux-config.guess.patch | OHOS平台补丁 | 使 config.guess 识别 OpenHarmony 系统标识 |
| 0002-build-aux-config.sub.patch | OHOS平台补丁 | 使 config.sub 接受 ohos/aarch64 目标三元组 |
| 0003-hmdfs-umask-and-autogen-fix.sh | HMDFS平台修复 | 1) autoreconf生成configure(GitHub tarball不含) 2) sed修复configure中umask 000→007 |

## HMDFS 平台注意事项

1. **autogen.sh**: GitHub release tarball (v3.1.12.tar.gz) 不含预生成的 `configure` 脚本，需先执行 `autoreconf --install --force` 或 `./autogen.sh`
2. **umask 陷阱**: autotools configure 用 `umask 000 && mktemp -d` 创建临时目录，在 HMDFS 上导致 conftest.c 在两次测试间被删除。修复: `sed -i 's/umask 000 && mktemp/umask 007 && mktemp/g' configure` (E088)
3. **运行时加载限制**: HMDFS 上共享库缺少 "other" read 权限位，动态链接器无法 mmap 加载。部署到标准 Linux 文件系统即可正常运行
4. **chmod 无效**: HMDFS 不支持 chmod 修改文件权限

## 依赖

无外部依赖。仅需标准 libc 头文件。

## 测试报告

详见 `reports/test-report.md`:
- T1-T8: ✅ PASS (文件验证、pkg-config、头文件、符号导出、编译链接测试)
- 运行时加载: ⚠️ BLOCKED (HMDFS权限限制，非编译缺陷)
- make check: ⏭️ SKIP (需要 Modbus TCP/串口硬件)

## SHA256

```
libmodbus.so.5.1.0: d85d0449d132a59b77ddcf841a7fe1ccbab31a27285b11c3aa41c8ba4dfdb9b5
```

## pkg-config 内容

```
prefix=/storage/Users/currentUser/usr/local
exec_prefix=${prefix}
libdir=${exec_prefix}/lib
includedir=${prefix}/include

Name: modbus
Description: Modbus library
Version: 3.1.12
Libs: -L${libdir} -lmodbus
Cflags: -I${includedir}/modbus
```