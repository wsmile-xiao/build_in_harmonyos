# id3v2 0.1.12 适配笔记

## 概述

id3v2 是基于 id3lib 的命令行 ID3v1/v2 标签编辑器，用于为 MP3 文件增删改查
ID3 标签。id3lib 是 2003 年的老 autotools 库，在本仓库中归档为 stub（无
conanfile.py，未发布到制品仓）。因此本配方将 id3lib 3.8.3 源码 vendor 进来
（conandata.yml 第二源，解压到 `_id3lib/`），静态编译为 libid3.a 后构建 id3v2
（superbuild）。

- 构建系统: id3v2 平 Makefile 源码 + vendor id3lib autotools
- 编译器: clang/clang++ (hnp)，libc++
- 平台: aarch64-unknown-linux-ohos

## 依赖

- zlib/1.3.1（制品仓）: id3lib 压缩帧需要，静态链入二进制（无运行时 libz 依赖）
- id3lib 3.8.3（vendor）: 静态编译 libid3.a

## 遇到的问题与解决

| # | 问题 | 根因 | 解决 |
|---|------|------|------|
| 1 | id3lib 未发布 | id3lib 归档为 stub，无 conanfile.py | vendor id3lib 3.8.3 源码到 `_id3lib/`，随配方构建（superbuild） |
| 2 | config.guess 无法识别平台 | 2003 版不知 aarch64/HarmonyOS | 补丁 0001 加 `*:HarmonyOS:*` 检测分支 |
| 3 | config.sub 拒绝 ohos 三元组 | 缺 linux-ohos 映射 | 补丁 0002 加 `linux-ohos*` 到 maybe_os/OS 白名单/`-ohos*` 映射 |
| 4 | configure 找不到 C++ 标准头 | hnp clang 默认搜索路径无 libc++ 头 | 显式 `CXXFLAGS/LDFLAGS=-stdlib=libc++` 与 `CXXCPP` |
| 5 | configure iomanip.h 检查失败 | 现代 C++ 已弃用 `<iomanip.h>` | 补丁 0003 移除 iomanip.h 检查 |
| 6 | id3lib 编译缺 zlib.h | id3lib configure 探测 zlib | CPPFLAGS 注入 zlib include（来自 zlib/1.3.1 依赖） |
| 7 | config.status umask 077 | 真实 worker HMDFS umask 077 致临时目录 owner 无写权限（E011） | 补丁 0003 改 umask 022（保持默认 TMPDIR，不重定向） |
| 8 | id3v2 链接缺 compress/uncompress | libid3.a 需 zlib | 链接加 `-lz`，按 `-lid3 -lz` 顺序（静态库） |
| 9 | id3v2 Makefile 链接 `-lz -lid3` 顺序错 | 静态库需被引用方在前；Makefile 顺序反 | 手工编译，按 `-lid3 -lz` 顺序链接 |
| 10 | 上游 tarball 含过期 .o/二进制 | 2010 年发布含预编译产物 | source() 阶段清理 `*.o` 与 `id3v2` 二进制 |
| 11 | id3lib_bitset 用 `<iostream.h>` | 现代 C++ 弃用 | 补丁 0004 改 `<iostream>` |
| 12 | 容器内 config.guess 报 darwin/aarch64 不识别 | 容器 uname=Linux（CI 为 HarmonyOS），且 2003 config.guess 不识 aarch64 | 显式传 `--build/--host=aarch64-unknown-linux-ohos`，绕过 config.guess |

## 构建流程（配方 build）

1. source(): 下载 id3v2（源码根）+ id3lib（`_id3lib/`），清理过期产物
2. apply_conandata_patches: 打 id3lib 的 4 个补丁（路径前缀 `_id3lib/`）
3. Stage 1 — id3lib: `./configure --disable-shared --enable-static` → `make -C src`
   → 得 `src/.libs/libid3.a`；拷贝 `include/id3/` + libid3.a 到 `_stage/`
4. Stage 2 — id3v2: 编译 convert/list/id3v2/genre 4 个 cpp → 按 `-lid3 -lz` 链接

## 验证

- 容器内 `conan create` 通过（含 test_package 真实运行）
- test_package: 写 ID3 tag 到最小 MP3，读回校验 artist 字段（`TPE1: HarmonyTest`）
- 产物: `bin/id3v2`（ELF arm64），zlib 静态链入，运行时仅依赖 libc++/libc

## 补丁说明

4 个补丁均为 vendor 的 id3lib 的 OHOS 平台适配 / C++ 现代化，patch 内路径带
`_id3lib/` 前缀，由 `apply_conandata_patches` 在源码根应用。id3v2 自身源码无需
补丁。
