# libprintsys — printcap parser

## 概述

libprintsys 是 gnulpr（GNU LPR-ng）项目的 C 语言支撑库，提供读写 `/etc/printcap`
的标准化 API，并为 gnulpr 的 printfilters 解析打印机条目与 capability 字段。
上游作者为 valinux.com 时代开发者（Ben Woodard、Nick Moffitt、Mark Fasheh），
最后一次上游变动可追溯到 2001 年，项目托管于 SourceForge 的 `lpr` 组。

**本仓库适配版本**：0.6（HarmonyOS PC aarch64 / musl）

## 功能概述

- 库 `libprintsys.so.1`（soname `libprintsys.so.1`，`-version-info 1:0:0`）
  - `lps_init` / `lps_end`：系统句柄生命周期
  - `printcap_init` / `printcap_end` / `printcap_write`：printcap 文件解析与回写
  - `printcap_get_printer_list` / `printcap_get_printer`：打印机条目与别名查询
  - `lps_pair_lookup` / `lps_pair_update` / `lps_num_pairs`：capability 键值对操作
  - 文档数据库属性走 TDB（`LPS_DOCDBPATH`）
- 命令行工具 `pcap`：解析并输出 `/etc/printcap`（安装于 `bin/pcap`，
  Debian 打包时将其挪到 `/usr/lib/printfilters/`）

## 依赖

| 依赖 | 版本 | 说明 |
|---|---|---|
| glib | 2.88.3 | 硬依赖：`g_malloc`/`GString`/`GHashTable`/`GList`/`GSList` |
| tdb | 1.4.15 | 硬依赖：`#include <tdb.h>`，`tdb_open/fetch/store/close` |
| pkgconf | 3.0.6 | tool_requires，构建期解析 flags |

## 上游与许可证

- Homepage: https://lpr.sourceforge.net/
- 许可证：GPL-2.0-or-later（依据 Debian `debian/copyright` 的 `License: GPL-2+`；
  上游 `libprintsys.spec` 自称 LGPL，以打包元数据为准）
- 源码获取：上游 SourceForge 文件区已无可用发布物，改用该源码包 `Vcs-Git`
  声明的官方仓库 salsa.debian.org 的 archive（详见版本目录 `notes.md`）

## 鸿蒙适配要点

上游是 autoconf 2.13 + libtool 1.3.3（1999）+ GLib 1.x `glib-config` 的远古组合，
在 OHOS 上需处理三元组识别、libtool 共享库判定与 `DT_NEEDED` 缺失三件事，
具体实证过程与已验证无效路线见 `0.6/notes.md`。
