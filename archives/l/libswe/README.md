# libswe

Astrodienst 高精度天文星历 C 库（Swiss Ephemeris）。

- 上游：https://github.com/aloistr/swisseph（tag v2.10.03）
- 主页：https://www.astro.com/swisseph/
- 许可证：AGPL-3.0-only（双许可：AGPL 或 Swiss Ephemeris 商业许可，见源码 LICENSE）
- 类型：C 库（library），产物 `lib/libswe.a`（默认）/ `lib/libswe.so`（`shared=True` 时）

## 功能概述

- 行星/月亮/小行星位置（swe_calc_ut / swe_calc）
- 恒星、日月食、升起落下、宫位、永久黄道岁差
- Moshier 解析历（免数据文件）与 Swiss/JPL 星历文件两种模式

## OHOS 适配

- 纯 Makefile 项目，无 configure/CMake；in-source 构建（对齐 `zlib/1.3.1`）。
- 只构建可移植目标（`libswe.a`、`libswe.so`、`swetest`、`swevents`、`swemini`）；跳过写死 RHEL 路径的 `swetests` 目标。
- 编译器取自 Conan conf（R33）；SHELL/TMPDIR 按已合入的 `bwm/0.6.3` 模式加固（不用 `/tmp`）。
- 上游 `setest` 测试框架（60 TESTCASE）在 `build()` 内完整构建并运行；`m4`/`openssl` 经 `tool_requires` 引入，仅供测试 harness 使用，不进入 `requires()`（产出库只链接 `libc/libm/libdl`）。
- SWIEPH/JPLEPH 用例需另行下载星历数据文件（上游发布包不含），豁免声明见版本内 `test_package/MANIFEST.yml`；消费者测试走免数据的 Moshier 路径。

## 依赖

- 编译：C 编译器 + make；无外部 Conan requires
- 测试构建：`m4/1.4.19`、`openssl/3.5.6.1`（tool_requires，仅测试用）
- 运行：`libm`、`libdl`（经 `system_libs` 声明）

## 参考

- 源码仓库：https://github.com/aloistr/swisseph
- 编程文档：上游 `doc/`（swephprg）
- 各版本详情见 `2.10.03/notes.md`
