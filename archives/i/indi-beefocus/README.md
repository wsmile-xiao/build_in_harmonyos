# indi-beefocus

## 软件描述

indi-beefocus 是 **Bee Focuser**（开源硬件/软件望远镜调焦器）的 INDI 驱动。
调焦器硬件基于 ESP8266 微控制器，通过 WiFi 以 TCP/IP 与上位机通信，本驱动
即上位机侧的 INDI 设备驱动：

- 绝对位置移动（`ABS_FOCUS_POSITION`）
- 相对位置移动（`REL_FOCUS_POSITION`）
- 移动中止（`FOCUS_ABORT_MOTION`）
- 位置同步 / 回零（`FOCUS_SYNC`、`FOCUS_HOME`）
- 连接状态与调焦器状态只读属性（`CSTATUS` / `FSTATUS`）

驱动同时内置**软件模拟固件**（`driver/beesimfirmware.cpp` 复用 `firmware/`
的同一套固件代码），因此无需真实硬件即可运行与测试——上游单元测试正是基于
该模拟固件。

上游项目：<https://github.com/indilib/indi-3rdparty>（`indi-beefocus/` 子目录）
硬件项目：<https://github.com/glowmouse/beefocus>

## 版本信息

- 当前版本：`0.1-20221222010828`（= 上游快照 `0.1+20221222010828`，日期戳
  2022-12-22 01:08:28；Conan 版本号把 `+` 规范化为 `-`）
- 源码：<https://salsa.debian.org/debian-astro-team/indi-beefocus>
  上游 tag `upstream/0.1+20221222010828`
- 许可证：LGPL-2.1+（`firmware/LICENSE`）

> 上游 indilib/indi-3rdparty **不为单个 3rdparty 驱动打 tag**，且该子项目在
> v2.2.x 系列中已不再随 monorepo tarball 发布。本仓库既有先例（libplayerone
> 3.1.0）对同类情况采用 salsa 官方上游 tag 快照，本配方沿用同一来源。
> 来源可信性已实证：该快照与 Debian 归档的 `orig.tar.gz` **逐文件、逐字节
> 完全一致**（95 个文件全量 sha256 比对，见版本目录 notes.md）。

## OHOS 适配

- **无构建目标变更**：仍用上游 CMake 构建；配方只做平台适配与配方侧注入。
- **E092**：CMake 不识别 HarmonyOS，强制 `CMAKE_SYSTEM_NAME=Linux`
  （经补丁 0004 写入上游 CMakeLists）+ `CMAKE_SYSTEM_PROCESSOR=aarch64`。
- **E537**：本平台无法对 Conan 缓存中的 OHOS 共享库做 `mmap PROT_EXEC` 加载
  （`libindidriver.so` / `libindiAlignmentDriver.so` 均 `Permission denied`），
  因此驱动**静态链接** `libindidriver.a`；同时需
  `-Wl,--allow-multiple-definition`（归档内 `indidrivermain.o` 自带 `main`/`me`）。
  这与本仓库 libindi 自身 test_package 的做法一致。
- 补丁 4 个：FindINDI 版本正则回移、C++14→17、INDI 1.x→2.x 属性 API 移植、
  上游两处构建缺陷修复（详见版本目录 notes.md）。
- 产物是**命令行驱动可执行文件**，故软件级提供 `commands.json`（R38/L0k）。

## 产物

| 路径 | 说明 |
|---|---|
| `bin/indi_beefocus` | INDI 驱动可执行文件（aarch64/OHOS） |
| `share/indi/indi_beefocus.xml` | INDI 驱动描述（供 indiserver / 客户端发现） |
| `licenses/LICENSE` | 上游 LGPL-2.1+ 许可证原文 |

## 使用方式

```sh
# 由 INDI 服务器拉起（推荐）
indiserver -v /path/to/bin/indi_beefocus

# 或单独运行，直接以 INDI XML 协议与 stdin/stdout 交互
./bin/indi_beefocus -v
```

连接调焦器：在 INDI 客户端（KStars / Xephem 等）中选择 “Bee Focuser”，
Connection 页可选择 *TCP Connect*（真实硬件，默认端口 4999）或
*Simulated Connection*（软件模拟，无需硬件）。

## 版本索引

| 版本 | 状态 | 构建日期 |
|---|---|---|
| `0.1-20221222010828` | built | 2026-10-03 |
