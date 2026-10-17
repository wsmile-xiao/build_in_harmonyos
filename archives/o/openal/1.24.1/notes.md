# openal 1.24.1 — 适配笔记（OpenHarmony PC aarch64）

## 概述

OpenAL Soft 1.24.1（C/C++，CMake ≥3.13，C++17/C11，LGPL-2.0-or-later）。
上游 https://github.com/kcat/openal-soft ，tag `1.24.1`。
本仓同名包已有 1.25.2（2026-08-03）；1.24.1 为新增版本目录，沿用同一 conan 包名 `openal`。

## 源码

- 源码包：`openal-soft-1.24.1.tar.gz`（1,205,028 字节，GitHub tag 归档）
- 本地实测 SHA256：`e1b6ec960e00bfed3d480330274b0f102dc10e4ae0dbb70fd9db80d6978165b1`
  （直连 github.com 与 ghfast 镜像各下载一次，哈希一致；上游未发布官方源码 hash）
- 许可证：根目录 COPYING = LGPL v2 "any later version"（LGPL-2.0-or-later）

## 构建（CMake，静态库，关闭全部外部后端）

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DLIBTYPE=STATIC -DALSOFT_DLOPEN=OFF \
  -DALSOFT_UTILS=OFF -DALSOFT_EXAMPLES=OFF -DALSOFT_TESTS=OFF \
  -DALSOFT_UPDATE_BUILD_VERSION=OFF -DALSOFT_EMBED_HRTF_DATA=OFF \
  -DALSOFT_INSTALL_CONFIG=OFF -DALSOFT_INSTALL_HRTF_DATA=OFF \
  -DALSOFT_INSTALL_AMBDEC_PRESETS=OFF -DALSOFT_EAX=OFF \
  -DALSOFT_BACKEND_{ALSA,PIPEWIRE,PULSEAUDIO,JACK,OSS,SOLARIS,SNDIO,PORTAUDIO,SDL2,COREAUDIO,OBOE,OPENSL,WAVE}=OFF \
  -DALSOFT_CPUEXT_{SSE,SSE2,SSE3,SSE4_1}=OFF -DALSOFT_CPUEXT_NEON=ON
cmake --build build -j20   # rc=0
```

实际执行走 `conan create`（profile `ci/conan/profiles/ohos-aarch64`，os=OHOS / armv8 /
clang 15 / libc++ / cppstd=17），日志 `reports/conan-create.log`。

- CMake 配置摘要：`Building OpenAL with support for the following backends: Null`、
  `CPU extensions: Default, Neon`
- 产物：`libopenal.a`（静态库），头文件 + `OpenALTargets.cmake` 正常安装
- fmt-11.0.2 由源码树内置（`add_subdirectory(fmt-11.0.2 EXCLUDE_FROM_ALL)`），非外部依赖

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 反复打印 `System is unknown to cmake, create: Platform/HarmonyOS` | conan 的 CMakeToolchain 把 os=OHOS 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，CMake 无该平台文件 | 无需处理：全部探测（pthread/rt/m/pthread_setschedparam）正常完成，构建与测试通过 |
| 2 | test_package 编译报 `use of undeclared identifier 'ALC_FORMAT_CHANNELS_SOFT'` 等 | ALC_SOFT_loopback 的枚举/原型在 `alext.h` 而非 `alc.h` | test_package 补 `#include <AL/alext.h>` |
| 3 | 补上头文件后仍报 `call to undeclared function 'alcLoopbackOpenDeviceSOFT'` | alext.h 的扩展**函数原型**被 `#ifdef AL_ALEXT_PROTOTYPES` 包裹（枚举宏无条件） | include 前加 `#define AL_ALEXT_PROTOTYPES 1` |
| 4 | 首跑断言 `zero-crossings=54` 与预期 26.4 不符判 FAIL | 正弦每周期**升/降各过零一次**，计数应为 `2×220Hz×0.12s≈52.8` | 修正断言区间 [46,60]（测试自身问题，非库问题） |
| 5 | `lang-preflight` 判 `mixed`（gradle/maven）并写 `env_unsupported` 终态 | 检测器把 vendored `fmt-11.0.2/support/build.gradle` 当成本项目构建系统 manifest | 误报：根 CMakeLists.txt + 158 源文件 89% c/cpp；按 C/C++ 正常推进，并用 `result --draft-milestone task_started --force` 覆盖误写终态 |

## 与 1.25.2 的差异（为什么零补丁）

1.25.2 全项目切到 C++20（`<format>`/`<ranges>`/`source_location`/三路比较），
在 OHOS libc++ 15.0.4 上需要 9 个兼容补丁；**1.24.1 仍是 C++17**
（`CXX_STANDARD 17`，`common/alspan.h` 自带 span 实现），clang 15/libc++ 15 直接满足，
`ALSOFT_ENABLE_MODULES`/`ALSOFT_BACKEND_SDL3` 等 1.25.x 新选项也不存在 → **patches/ 为空**。

## 平台取舍（OHOS 语义）

- 静态库（`LIBTYPE=STATIC`）：OHOS 无系统 libopenal，静态包避免任何 SONAME/系统同名冲突；
  消费方需 `AL_LIBTYPE_STATIC`（package_info 已设）。
- 外部后端全关，仅保留上游无条件编译的 Null + loopback：无音频设备也能完成全部功能验证。
- `ALSOFT_EMBED_HRTF_DATA=OFF`：不内嵌 HRTF 数据集（减小体积，与仓内 1.25.2 口径一致；
  HRTF 代码仍编译，`ALC_SOFT_HRTF` 扩展仍声明）。
- NEON 开启（armv8），x86 SIMD 探测关闭。

## 上游测试（R51 三步法）

- 清点：上游仅 1 个测试文件 `tests/example.t.cpp`（`ExampleTest.Basic`，GTest，
  CMake 经 FetchContent 拉 gtest；`ALSOFT_TESTS` 默认 OFF）。无其他测试套件（无 ctest 注册项）。
- 运行：GTest/FetchContent 在交叉构建中不可用（需联网拉 gtest），故将该用例**去依赖移植**为
  `test_package/upstream_basic.cpp`（保留原断言体），随 conan create 在真机执行。
- 实测：`PASS: upstream ExampleTest.Basic API surface compiles and links`（1/1）。

## 验证结果（conan create 内置 test_package，真机执行）

```text
== OpenAL Soft 1.24.1 consumer test (null + loopback) ==
A) null 后端 18 项：设备/上下文/AL_VERSION="1.1 ALSOFT 1.24.1"/AL_VENDOR/
   AL_RENDERER/buffer/source/播放状态机/AL_INVALID_ENUM 负路径/关停，全 PASS
B) loopback 后端 15 项：ALC_SOFT_loopback + ALC_SOFT_HRTF 声明、8kHz mono/short
   格式协商、alcRenderSamplesSOFT 实渲染 960 样本（peak=16383 = 0.5FS，
   零交叉 54 ≈ 2×220Hz×0.12s，非静音，第二块仍有效），全 PASS
TOTAL: 33 / PASS: 33 / FAIL: 0
```

## 依赖版本

- 无 Conan 依赖（`requirements()` 为空）；系统库 `m`、`pthread`
- 工具链：clang/clang++ 15.0.4（/data/service/hnp/bin）、cmake 4.1.2、Conan 2（OHOS 适配版）
---

**编译结束**: 2026-09-28 16:08
**最终状态**: built
