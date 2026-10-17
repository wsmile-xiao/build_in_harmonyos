# laz-perf — PDAL 使用的 LAS/LAZ（LiDAR 点云）读写与压缩编解码库

lazperf 是 LAS/LAZ 格式的 C++ 读写库：实现 **LASzip 分块压缩编解码器**、
LAS 1.2 / 1.3 / 1.4 的 header 模型，以及一套流级文件 API。PDAL 用它读写
LAZ（压缩的 LAS）点云文件。上游仓库 https://github.com/hobuinc/laz-perf
（默认分支 master），本仓库适配 tag **3.4.0**（Conan 包名 `laz-perf`，与站内 `lazperf/3.4.0` 同源）。

## 功能概述

- **流级文件 API**（推荐入口）：`reader::named_file` / `writer::named_file`
  按文件名打开 LAS/LAZ，`readPoint()` / `writePoint()` 逐点读写，
  `header()` 给出解析后的 header，关文件时自动收尾。
- **header 模型**（`lazperf/header.hpp`）：`header12` / `header13` / `header14`
  三种版本，`baseCount(point_format_id)` 给出基础点记录长度
  （format 0 → 20 字节、format 3 → 34、format 6 → 30）。
- **VLR**（`lazperf/vlr.hpp`）：LASzip VLR 结构（`laszip_vlr`，含
  `compressor` / `chunk_size` / `ver_major` / `ver_minor` / `revision` 与 item 表），
  以及 LAS 的 VLR 列表读写。
- **编解码器**（`lazperf/lazperf.hpp`）：`writer::chunk_compressor` /
  `reader::chunk_decompressor`，可在任意（含**非对齐**）缓冲区上工作，
  支持按 chunk 并行压缩（同参数下输出逐字节确定）。
- **LAS ↔ LAZ 转换工具**：`las2laz` / `laz2las`（`cpp/tools/`，需 `WITH_TESTS` 之外的
  tools 子目录，见下）。

## OHOS 适配要点

- **测试夹具写死 `/var/tmp`（E002 家族）**：`cpp/test/io_tests.cpp` 的
  `makeTempFileName()` 把临时 LAS/LAZ 文件写死在 `/var/tmp/fnXXXXXX`，并且
  **忽略 `mkstemp()` 的返回值**。OHOS 根文件系统只读、`/var/tmp` 可能根本不存在，
  于是 `mkstemp` 失败被吞掉、随后的 `ofstream` 静默产出**空文件**，用例以
  「读回来的内容不对」失败——表象指向数据，实际是路径不可写。
  实测（`mount -t tmpfs -o ro /var/tmp`）：未打补丁 **21 ran / 14 PASSED /
  7 FAILED**，失败的正是调用 `makeTempFileName()` 的 7 个用例；打上
  `patches/0001` 后 **21/21**。补丁改成按 POSIX 解析 `$TMPDIR`、退回当前目录，
  属**通用可移植性修复**，可直接上游（P005/P014）。
- **configure 期直连 GitHub**：顶层 `CMakeLists.txt` 在 `WITH_TESTS` 打开时执行
  `file(DOWNLOAD https://github.com/PDAL/data/raw/master/autzen/autzen.laz)`。
  CI 只能经镜像取 tarball，不应直连 github.com；而这个文件本构建无人消费——
  只有 `cpp/benchmarks/laszip.cpp` 读它，且该目标要在找到**外部** LASzip
  （`LASZIP_FOUND`）时才 `add_executable`，实际不会建立；所有 ctest 用例用的是
  tarball 自带的 `autzen_trim.las`/`.laz`。`patches/0002` 把下载收进默认 OFF 的
  `LAZPERF_FETCH_TEST_DATA` 选项（与 `DRAFT-isutf8-cmake-configure-download-benchmarks`
  同类先例）。
- **内置 gtest 的 CMake 下限**：`cpp/test/gtest/gtest-10-06-21/googletest/CMakeLists.txt`
  仍写 `cmake_minimum_required(VERSION 2.8.12)`，CMake ≥ 4 直接拒绝。配方用
  **cache** 变量钉 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（用普通 `tc.variables` 不会
  进 CMakeCache，压不住）。gtest 1.10.0 随 tarball 内置，configure 期不联网取测试框架。
- **gtest 的 `-Werror`**：gtest 自带 `-Wall -Wshadow -Werror -Wconversion`，
  而 OHOS clang driver 会把**它自己注入的** flag 报成
  `-Wunused-command-line-argument`。只关这一条诊断（E293 模式的**有界收敛**），
  不用 blanket `-Wno-error`，不动任何断言。
- **ctest 的工作目录**：上游 `add_test()` 用
  `WORKING_DIRECTORY "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/../.."`，而
  `CMAKE_RUNTIME_OUTPUT_DIRECTORY` 全树未设置 → 解析成 `/`。配方在
  `build_folder/tmp` 建可写目录，把 `TMPDIR`/`TMP`/`TEMP` 注入给 ctest
  （与补丁 0001 的 `$TMPDIR` 优先级配套）。`CMake.ctest()` 由 Conan 在
  `build_folder` 里执行，无需 `--test-dir`。
- **安装产物与上游 `install()` 对齐**：上游只装 6 个 stream 级头文件
  （`lazperf.hpp`、`filestream.hpp`、`header.hpp`、`readers.hpp`、`vlr.hpp`、
  `writers.hpp`）+ `lazperf_user_base.hpp` **改名**为 `lazperf_base.hpp`；
  且只装 **shared** 一种 flavour 的 target。默认的 static 构建若走
  `cmake.install()` 会一个库都装不出来，故 `package()` 直接从 build 树取
  `liblazperf_s.a`（static）/ `liblazperf.so`（shared），头文件集合逐一对齐。

## 依赖关系

### 编译依赖
- 无第三方依赖。gtest 1.10.0 已随 tarball 内置，无需 `tool_requires`。
- C++17（上游 `set(CMAKE_CXX_STANDARD 17)`）。

### 运行依赖
- `libc++_shared.so`（OHOS 上 C++ 运行时）；纯 C++ 实现，无外部库依赖。

## 版本

| Version | Status |
| --- | --- |
| 3.4.0 | built |

## 已知上游注意事项

- 上游同时存在 `cpp/lazperf/lazperf_base.hpp` 与 `cpp/lazperf/lazperf_user_base.hpp`
  两个文件，内容**不一致**：前者写 `LAZPERF_VERSION 3.2.0` + `__declspec(dllexport)` /
  visibility 属性，后者写 `LAZPERF_VERSION 1.3.0` + 空的 `LAZPERF_EXPORT`。
  源码树内 `lazperf.hpp` / `header.hpp` `#include "lazperf_base.hpp"` 拿到的是**前者**；
  而 `install()` 装的是把**后者**改名成 `lazperf_base.hpp`。于是在树内构建与安装后
  消费，`LAZPERF_VERSION` 宏的取值不同（3.2.0 vs 1.3.0）。本适配不依赖该宏，
  消费者也不应据此判版本——请以 Conan 包版本 `lazperf/3.4.0` 为准。
- 3.4.0 的 `cpp/test/stream_tests.cpp` 里唯一用例 `streams_are_sane` 被上游用
  `/** ... **/` 块注释掉了，因此该测试可执行断言为 0（但仍真实编译、真实被 ctest
  运行）。统计上游测试数时须如实计入「未执行」，不能算作通过。

## 参考链接

- 上游仓库：https://github.com/hobuinc/laz-perf
- release tag：`3.4.0`（无 `v` 前缀）
- LAS 规范：https://www.asprs.org/divisions-committees/lidar-division/laser-las-file-format-exchange-activities
- 许可证：Apache-2.0
