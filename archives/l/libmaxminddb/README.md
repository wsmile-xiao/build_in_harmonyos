# libmaxminddb

`libmaxminddb` 是 MaxMind DB（.mmdb，GeoIP2/GeoLite2）格式的 C 语言读取库，提供快速的内存映射（mmap）查询 API，并附带 `mmdblookup` 命令行工具。

上游 [GitHub maxmind/libmaxminddb](https://github.com/maxmind/libmaxminddb)（Apache-2.0）。

## 功能概述

- 库：`MMDB_open` / `MMDB_lookup_string` / `MMDB_get_value` / `MMDB_close` 等完整读 API（mmap/文件流双模式）
- 工具：`mmdblookup` CLI（查 IP → 输出记录字段）
- 支持 IPv4/IPv6 查找、嵌套 map/数组结构读取、线程安全（-pthread）

## 依赖关系

- 编译依赖：无第三方库（仅标准 POSIX 头 + `clock_gettime`/`open_memstream`，OHOS musl 均有）
- 运行依赖：libc；`AC_SEARCH_LIBS` 可能引入 `-lm`（已在 cpp_info.system_libs 声明）

## OHOS 适配要点

- conan 配方 `archives/l/libmaxminddb/1.13.3/conanfile.py`，autotools 构建，显式
  `--host=aarch64-linux-ohos --build=aarch64-linux-ohos`（上游 config.sub 原生支持
  `linux-ohos` 三元组，无需 config.guess/config.sub 补丁；显式三元组使 configure
  判定 cross_compiling=yes，AC_C_BIGENDIAN 走编译期 BYTE_ORDER 路径，不执行 aarch64 二进制）
- `make check` 不在 CI 执行：check_PROGRAMS 为 aarch64 OHOS 二进制，x86_64 构建机
  无法运行（exec format error），须在 OHOS 真机/模拟器上执行（R51 测试台账见 notes.md）
- 补丁 2 个（均已在 conandata.yml 声明）：
  - `0001-t-makefile-libtap-out-of-tree.patch`（E547）：t/Makefile.am + .in 的
    all-local/clean-local 用 `$(top_srcdir)` 前缀，修复 conan out-of-tree 构建
    `cd libtap: No such file or directory`
  - `0002-configure-umask-tmpdir.patch`（E046 族）：configure 临时目录 umask 077→007
    并改到 `${TMPDIR:-$HOME/tmp}`，修复 HMDFS setgid 构建目录下
    `./confXXXXXX/subs1.awk: Permission denied`
- 已移除 2026-05-06 原生构建遗留的 3 个陈旧补丁（config.guess/config.sub 升级版、
  configure tmp 目录），理由见 notes.md

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.13.3 | published | conan-verify G0–G4 全 PASS（2026-09-24），本次适配提交 |
| 1.11.0 | built | 旧版完整适配目录（main 既有） |

## 参考资料

- 上游仓库与发布：<https://github.com/maxmind/libmaxminddb/releases>
- 适配笔记：`archives/l/libmaxminddb/1.13.3/notes.md`
- 源码校验：sha256 见 `archives/l/libmaxminddb/1.13.3/conandata.yml`（与 manifest.yaml 双处声明）
