# libdivecomputer 0.9.0 — 移植笔记

状态：ohos-aarch64 conan create 完成（static/shared 双模式均通过）。

## 上游事实

- 官方源码：`libdivecomputer-0.9.0.tar.gz`
  - URL: https://github.com/libdivecomputer/libdivecomputer/releases/download/v0.9.0/libdivecomputer-0.9.0.tar.gz
  - sha256: `a7b80b9083a2113a43280ee7b51d48d66ea5a779fc3fee57df7c451da0251c65`
  - 685149 字节，顶层目录 `libdivecomputer-0.9.0`，对应 git tag `25b8fed709106dc693baad13eb47297abba46d98`
- License: LGPL-2.1-or-later（源文件头 + COPYING）
- 构建系统：autotools（`configure` + libtool `LT_INIT([win32-dll])`）
  - `lib_LTLIBRARIES = libdivecomputer.la`（src/Makefile.am），`-no-undefined`，libtool 默认同时构建 static+shared
  - `bin_PROGRAMS = dctool`（examples/，`--enable-examples` 默认 yes，可 `--disable-examples`）
  - `pkgconfig_DATA = libdivecomputer.pc`（顶层 Makefile.am）
  - configure 选项：`--enable-examples/--disable-examples`、`--enable-doc`（默认 yes）、`--enable-pty`（默认 no）、`--enable-logging`（默认 yes，ENABLE_LOGGING 宏）、`--with-libusb[=PKG]`、`--with-hidapi[=PKG]`、`--with-bluez[=PKG]`（PKG 默认分别为 `libusb-1.0`、`hidapi`、`bluez`）
  - 无 `make check`/`make test` 目标，无 tests/ 目录

## 真实依赖与 backend 矩阵（configure 事实）

| transport | 控制项 | 依赖 | 缺失时行为 |
|-----------|--------|------|------------|
| serial | 非_win32_ 恒开 | 无（POSIX termios） | — |
| usb | `--with-libusb` | pkg-config libusb-1.0 | HAVE_LIBUSB 未定义，usb.c 为 stub |
| usbhid | `--with-hidapi` 或 (libusb 且非 mac) | hidapi 或 libusb | USE_LIBUSB 回退或 stub |
| irda | 头探测 linux/irda.h | 无 | OHOS 无此头 → 空操作 |
| bluetooth | `--with-bluez` | pkg-config bluez | bluetooth.c 为 stub |
| ble | 无开关 | — | 上游硬编码 `transport_ble=no`（0.9.0 ble.c 仅公共 API 壳） |

- 所有 backend 缺失时库照常构建，运行时返回 `DC_STATUS_UNSUPPORTED`；**构建不以任何硬件为前提**
- libusb 1.0.27 在制品仓有 ohos-aarch64 二进制 → `with_libusb` 默认 True（真实依赖、真实 backend）
- hidapi 默认 False（usbhid 已由 libusb 回退覆盖）；bluez 默认 False 且 OHOS 下 validate 拒绝（bluez 5.79 OHOS 包为 daemon/tool 中心，未验证为库消费者场景；Linux 可开）

## 上游正式测试数量：0

- 顶层/src Makefile.am 无 check/test 目标；无 gtest/pytest/ctest/tests 目录
- `examples/dctool`（version/list/parse/scan/download/dump/read/write/timesync/fwupdate）是**手动 CLI 工具**，不是测试 harness 的一部分，不计入正式测试
- dctool 子命令中：`version`/`list`/`parse`（配原始数据文件）离线可用；`scan`/`download`/`read`/`write`/`timesync`/`fwupdate` 需真实潜水电脑（serial/USB/Bluetooth 硬件）
- 构建后已用 `dctool version`（输出 `libdivecomputer version 0.9.0`）与 `dctool list`（356 设备）做集成冒烟——不冒充测试

## 可离线验证范围（test_package 设计依据）

公开 API 中无需硬件的路径：
- `dc_version` / `dc_version_check` / `DC_VERSION_*` 宏（version.h.in/version.c）
- `dc_context_new/set_loglevel/get_transports/free`（context.h 全部 API）
- `dc_descriptor_iterator_new/next/free` 全量枚举设备库（descriptor.h，实测 356 个设备）
- `dc_parser_new2/get_type/get_field/samples_foreach/destroy` 解析内存构造数据（parser.h）
- 合成 Suunto Solution 剖面（src/suunto_solution_parser.c 语义逐步核实）：
  `data = 00 00 00 | 0A 0A 0A 0A | 80 | 05` → nsamples=4、divetime=(4*3+5)*60=1020s、maxdepth=40ft=12.192m

## OHOS 适配点（真实根因，全部实测复现）

1. **config.sub 不识别 ohos**：tarball 内 config.sub（2022-01-03）拒绝 `aarch64-unknown-linux-ohos`
   → patch 接受 `ohos*`（OS 列表）/`linux-ohos*`（kernel-os 组合）。
2. **config.guess 不认识 HarmonyOS uname**：`UNAME_SYSTEM=HarmonyOS` 无匹配 case →
   "unable to guess system type"。patch 增加 `*:HarmonyOS:*:*` case 输出
   `aarch64-unknown-linux-ohos`（与 acpid 2.0.34 先例同法）。
3. **umask 077 → HMDFS 临时目录不可写（E011）**：configure 与 config.guess 用
   `umask 077 && mktemp -d` 创建的目录在 HMDFS 上得到 0700+setgid（2700）模式，
   进程无法在其中创建 dummy.c 等文件（Permission denied）。实测 toybox mktemp：
   umask 077 → 2700 → 写失败；umask 022 → 2751 → 写成功。patch 将两处
   `umask 077` 改为 `umask 022`（libusb 1.0.27 先例同法）。
4. **libtool + clang/lld 嵌入宿主缓存 RUNPATH**：`hardcode_libdir_flag_spec
   ="-rpath <dir>"` 使 pkg-config 提供的 `-L~/.conan2/.../libusb/lib` 被硬编码进
   `libdivecomputer.so.0.0.0` 与 `dctool` 的 DT_RUNPATH。package() 用纯 Python ELF
   patch 将 DT_RUNPATH/DT_RPATH 表项改写为 DT_FLAGS=0（良性忽略标签）。
5. **ELF 修改后必须重签（E077）**：链接时 `-Wl,--code-sign` 生成的 .codesign 段在
   RUNPATH 改写后失效，加载器拒绝加载（"Error loading shared library"）。strip 后
   用 binary-sign-tool 重签（工具路径 CI 与开发机不同：/data/service/hnp/bin 与
   ~/usr/local/bin，配方按序探测）。已闭环实测：strip→重签→test_package 全过。
6. serial：`serial_posix.c` 仅标准 POSIX termios，OHOS musl 提供（无 TCGETA，E565 不适用）
7. irda：`linux/irda.h` 头探测在 OHOS 自然失败 → 空操作（合法）
8. BLE：上游 0.9.0 硬编码关闭（`transport_ble=no`）
9. R9：`make -j1` 串行构建

## 构建结果（ohos-aarch64，本机 localfix profile）

- static（shared=False）：rc=0。libdivecomputer.a 114 个成员全部 ELF64/AArch64；
  test_package 20 项 CHECK 全过（含 USB/USBHID 真实后端断言）。
- shared（shared=True）：rc=0。libdivecomputer.so.0.0.0：ELF64/AArch64、
  SONAME=libdivecomputer.so.0、NEEDED=libusb-1.0.so.0+libc.so（全目标侧）、
  RUNPATH 无宿主路径；test_package 20 项 CHECK 全过；dctool 可运行（version/list）。
- configure 确认（两种模式均）：Serial=yes USB=yes USBHID=yes（libusb 回退）
  IrDA=no Bluetooth=no BLE=no；HAVE_LIBUSB=1 实际生效（transports mask=0x07）。

## 硬件依赖测试的如实说明

- `scan`/`download`/`read`/`write`/`timesync`/`fwupdate` 需连接真实潜水电脑
  （serial/USB/Bluetooth），本环境无设备，未执行也不伪造
- 这些路径的可用性由编译期 backend 掩码断言（USB|USBHID 必须在 mask 中）间接保证，
  运行时行为（设备枚举、传输）无法离线验证

## 知识库

- 复用：E011（umask 077→022）、E077（ELF 修改后重签）、acpid 2.0.34（config.guess
  HarmonyOS case + config.sub ohos）、libusb 1.0.27（umask patch 先例）
- 路径 A：所有根因均有既有条目/先例覆盖，无新增 OHOS 平台根因，未新增 DRAFT
