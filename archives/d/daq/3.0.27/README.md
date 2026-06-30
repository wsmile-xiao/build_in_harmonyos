# DAQ（数据采集库）3.0.27 — HarmonyOS 预编译包

## 简介

DAQ（Data Acquisition Library，数据采集库）是 Snort 网络入侵检测系统使用的数据采集框架。它为网络数据包捕获提供了一个抽象接口层，支持多种数据采集模块，使 Snort 能够灵活选择不同的抓包方式。

本项目为 DAQ 3.0.27 编译的 HarmonyOS（鸿蒙）预编译包，目标架构为 `aarch64-unknown-linux-ohos`。

## 版本信息

| 项目 | 值 |
|------|-----|
| 软件名称 | libdaq |
| 版本号 | 3.0.27 |
| 构建系统 | autotools |
| 目标平台 | aarch64-unknown-linux-ohos (HarmonyOS) |
| 编译器 | clang 15.0.4 / clang++ 15.0.4 |
| 打包产物 | daq-3.0.27-ohos-aarch64.tar.gz |

## 包含的模块

### 可用模块（已编译）

| 模块名 | 类型 | 说明 |
|--------|------|------|
| afpacket | 共享 + 静态 | AF_PACKET 套接字接口模块，直接与 Linux 内核网络数据包交互 |
| fst | 共享 + 静态 | Flow Stream Tracker（流跟踪模块），用于跟踪网络流状态 |
| savefile | 共享 + 静态 | 离线 pcap 文件读取模块，从已保存的 pcap 文件中读取数据 |
| trace | 共享 + 静态 | 数据包追踪/调试模块，用于记录和调试数据包流 |
| gwlb | 共享 + 静态 | Gateway Load Balancer（网关负载均衡模块） |

### 禁用模块（未编译）

| 模块名 | 原因 |
|--------|------|
| pcap | 手动禁用（`--disable-pcap-module`） |
| bpf | 自动禁用（依赖 libpcap） |
| dump | 自动禁用（依赖 libpcap） |

> **说明**：libpcap 预编译包下载文件为空壳/损坏数据，因此无法启用 pcap 相关模块。若未来获得可用的 libpcap 预编译包，可重新编译并启用这些模块。

## 安装文件列表

### 共享库
- `lib/libdaq.so` → `lib/libdaq.so.3` → `lib/libdaq.so.3.0.0`
- `lib/daq/daq_afpacket.so`
- `lib/daq/daq_fst.so`
- `lib/daq/daq_savefile.so`
- `lib/daq/daq_trace.so`
- `lib/daq/daq_gwlb.so`

### 静态库
- `lib/libdaq.a`
- `lib/libdaq_static_afpacket.a`
- `lib/libdaq_static_fst.a`
- `lib/libdaq_static_savefile.a`
- `lib/libdaq_static_trace.a`
- `lib/libdaq_static_gwlb.a`

### 头文件
- `include/daq.h` — DAQ 主接口头文件
- `include/daq_common.h` — DAQ 通用定义
- `include/daq_dlt.h` — 数据链路类型定义
- `include/daq_module_api.h` — DAQ 模块 API 接口
- `include/daq_version.h` — 版本信息

### pkg-config 文件
- `lib/pkgconfig/libdaq.pc`
- `lib/pkgconfig/libdaq_static_afpacket.pc`
- `lib/pkgconfig/libdaq_static_fst.pc`
- `lib/pkgconfig/libdaq_static_savefile.pc`
- `lib/pkgconfig/libdaq_static_trace.pc`
- `lib/pkgconfig/libdaq_static_gwlb.pc`

### 测试程序
- `bin/daqtest` — DAQ 测试程序（动态链接）
- `bin/daqtest-static` — DAQ 测试程序（静态链接 DAQ 模块）

## 编译配置

```bash
# 构建步骤
autoreconf -ivf
TMPDIR=/storage/Users/currentUser/tmp ./configure \
  --prefix=/storage/Users/currentUser/usr/local \
  --disable-pcap-module
make -j1
make install
```

## 编译依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| clang/clang++ | 15.0.4 | HarmonyOS SDK 编译器 |
| autoconf | 2.72 | 用于生成 configure 脚本 |
| automake | 1.16 | 用于生成 Makefile |
| libtool | — | 用于构建共享库 |
| pkg-config | 0.29.2 | 提供 pkg.m4 宏 |

## 补丁说明

本预编译包需要 9 个补丁才能在 HarmonyOS 上成功编译：

1. `0001-aclocal.m4.patch` — 添加 pkg.m4 等宏定义
2. `0002-aminclude_static.am.patch` — 静态检查宏
3. `0003-ar-lib.patch` — ar 工具辅助脚本
4. `0004-compile.patch` — 编译辅助脚本
5. `0005-config.guess.patch` — OHOS 平台识别补丁
6. `0006-config.sub.patch` — OHOS triplet 验证补丁
7. `0007-configure.patch` — 重新生成的 configure 脚本（含 OHOS 修复）
8. `0008-install-sh.patch` — 安装辅助脚本
9. `0009-missing.patch` — 缺失工具辅助脚本

### 关键修复

- **config.guess/config.sub**：打 OHOS 补丁使系统能识别 `aarch64-unknown-linux-ohos` triplet
- **config.sub linux-ohos**：在 `case $kernel-$os-$obj` 行添加 `linux-ohos*-` 验证规则
- **HMDFS umask 问题**：`config.status` 中 `umask 077 && mktemp -d` 创建的临时目录在 HMDFS 上无法写入文件，需改为 `umask 000`

## 使用方法

### 安装预编译包

```bash
# 解压到目标目录
tar xzf daq-3.0.27-ohos-aarch64.tar.gz -C /path/to/install
```

### 通过 pkg-config 验证

```bash
export PKG_CONFIG_PATH=/path/to/install/lib/pkgconfig
pkg-config --modversion libdaq    # 输出: 3.0.27
pkg-config --libs libdaq           # 输出: -L/path/to/install/lib -ldaq -ldl
pkg-config --cflags libdaq         # 输出: -I/path/to/install/include
```

### 编写使用 DAQ 的程序

```c
#include <daq.h>

int main() {
    DAQ_Config config;
    DAQ_Init();
    // 配置 DAQ 模块...
    return 0;
}
```

## 注意事项

1. **HMDFS 文件系统限制**：
   - `/tmp` 目录不可写，需设置 `TMPDIR=/storage/Users/currentUser/tmp`
   - `umask 077` 创建的目录无法写入文件，需改为 `umask 000`
   - HMDFS 软链接不能 `ln -sf` 覆盖

2. **autoreconf 前置步骤**：
   - 需在 `m4/` 目录添加 `pkg.m4`（来自 pkg-config 0.29.2）
   - 需创建 `autoconf` 符号链接

3. **libpcap 缺失**：
   - pcap/bpf/dump 模块不可用，相关功能（如实时抓包）受限制
   - 建议后续编译 libpcap 预编译包后重新编译 DAQ 以启用完整功能

## 许可证

DAQ 使用 BSD 许可证，详见源码中的 LICENSE 文件。