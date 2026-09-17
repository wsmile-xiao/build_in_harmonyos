# libsbsms

libsbsms（Subband Sinusoidal Modeling Synthesis）是一个用于音频**变速**（time stretching）
与**变调**（pitch scaling）的高质量 C++ 库，采用八度子带正弦建模实现，是 Audacity
“Change Tempo / Change Pitch”效果的 DSP 内核。

## 功能概述

- 时间伸缩（tempo/rate 变化）而不改变音高；
- 音高平移（半音/倍频程）而不改变时长；
- 支持线性/几何的速率与音高滑动（`Slide`）；
- 多声道（1–2 声道）处理；
- 可从内存或回调流式输入（`SBSMSInterface` / `SBSMSInterfaceSliding`），
  输出永不结束（库持续补零），由消费者按 `getSamplesToOutput()` 决定停止；
- 可选渲染器接口（`SBSMSRenderer`）用于导出中间轨道数据。

## OHOS 适配

- **构建系统用 CMake**。仓库里同时提交了 autotools 与 CMake 两套构建：
  CMake 是上游 `.github/workflows/build.yml` 实际使用的路径，且 `project()` 版本是
  真实的 2.3.0；commit 里的 `configure.ac` 仍写 2.2.0/2.1.0（`sbsms.pc` 版本与
  libtool `-version-info` 因此是陈旧的）。选 CMake 同时避开了老
  `config.guess`/`config.sub` 不认识 aarch64-ohos 三元组的问题。
- **CMake 4.x 策略下限**：上游 `cmake_minimum_required(VERSION 3.1)` 会被 CMake 4.x
  直接拒绝，配方以 cache 变量注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
- **平台名必须显式指定为 `OHOS`**：Conan 把 `os=OHOS` 映射成
  `CMAKE_SYSTEM_NAME=HarmonyOS`，而 CMake 没有 `Platform/HarmonyOS.cmake`，
  于是共享库 SONAME 链接标志为空、`SOVERSION`/`VERSION` 被静默忽略（产物无
  `DT_SONAME`）。worker CMake 与 OHOS SDK CMake 都自带
  `Modules/Platform/OHOS.cmake`（即 `include(Platform/Linux)`），显式选择它即可
  产出 `libsbsms.so.2`。
- 源码零补丁：OHOS SDK clang 可直接编译，无需平台宏或 `#ifdef __OHOS__` 分支。
- 已知限制：无。库不提供命令行工具。

## 依赖关系

- 编译依赖：无（自包含，仅需 C++ 编译器与 CMake）。
- 运行依赖：无（仅 libc / libc++）。

## 上游测试

上游 2.3.0 **不随源码提供任何测试**：无 `test/` 目录、`src/` 中无 `main()`、
顶层 `Makefile.am` 的 `SUBDIRS` 只有 `src`。本归档的 `test_package/` 提供消费者侧
API 往返测试（26 条断言）。

## 参考资料

- 源码仓库：<https://github.com/claytonotey/libsbsms>
- 历史主页：<http://sbsms.sourceforge.net/>（已不再提供下载）
- 公开 API：`include/sbsms.h`
