# barrier 2.4.0 — 鸿蒙 PC (OHOS armv8) 适配笔记

> 探索式编译记录。构建系统：CMake。GUI 依赖 Qt5。GPLv2。
> 源码：https://github.com/debauchee/barrier (v2.4.0, tag)
> 说明：适配方向为 **BARRIER_BUILD_GUI=OFF**（CLI 核心 barriers/barrierc，KVM 主功能）。
>       Qt5 GUI 为已知限制：ohpcd `qt5-qtbase/5.15.2` 二进制为 -no-widgets，
>       不暴露 Qt5::Widgets，GUI 无法链接；详见进度与下方"已知限制"。

## 依赖清单（源码 CMakeLists.txt 核实）

| 依赖 | 需求 | 说明 |
|------|------|------|
| Qt5 (Core/Widgets/Network) | GUI 硬性 | 使用 ohpcd `qt5-qtbase/5.15.2`；配方须 `set_property("qt5-qtbase","cmake_file_name","Qt5")` |
| CURL | 硬性（根 CMakeLists.txt:132 FATAL） | `libcurl/8.5.0`（静态+fPIC） |
| OpenSSL | 硬性（根 CMakeLists.txt:370 `ssl crypto`） | `openssl/1.1.1w`（静态） |
| XTest.h/Xtst | 硬性（根 CMakeLists.txt:197,232 FATAL） | `libxtst/6.1.0` |
| libX11/XKBlib | GUI 硬性（根 CMakeLists.txt:201 FATAL） | `libx11/6.4.0`（与 X11 族 6.4.Z 区间一致） |
| dns_sd (avahi) | GUI 硬性（根 CMakeLists.txt:205） | `avahi-compat-libdns_sd/0.9_rc5` |
| libXi/Xinerama/Xext/Xrandr/SM/ICE | 可选（check_library_exists） | Xrandr ohpcd 无制品；Xi 需 `libxi/6.1.0` |
| gtest/gmock | 测试（BARRIER_BUILD_TESTS） | 需 vendor 源码到 ext/ |

## 已确认的 OHOS 适配点（探索 compile 暴露）

### P1. CMake 版本不兼容
`cmake_minimum_required(VERSION 3.4)` 与 CMake 4.1.2 冲突（<3.5 支持已移除）。
→ configure 需加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`，或在配方中直接 patch CMakeLists。

### P2. vendor 子模块源码缺失
tarball 的 `ext/gtest`、`ext/gmock`、`ext/gulrak-filesystem` 是空 git 子模块，但
`cmake/gtest.cmake` 无条件 `include` 并以 `../ext/gtest/src/gtest-all.cc` 构建。
→ 需 vendor：google/googletest（release-1.11.0）放 `ext/gtest`+`ext/gmock`，
gulrak/filesystem 头文件放 `ext/gulrak-filesystem/include/ghc`。
（已在工作树验证，详见下方"已 vendor"）

### P3. CMAKE_SYSTEM_NAME=HarmonyOS 使 CMake 无 Unix 平台模块（★ 核心）
OHOS 工具链设 `CMAKE_SYSTEM_NAME=HarmonyOS`，CMake 4 无 HarmonyOS 平台模块，
导致 `UNIX` 变量为空 → 所有 `if (UNIX)` 分支跳过 → X11/curl/pthread 库检测与
`src/lib/platform` 的 XWindows glob 全失效（报 "No SOURCES"）。
→ 配方 generate() 必须强制 `CMAKE_SYSTEM_NAME=Linux`（触发上游 Linux 分支）。
   - 实现：在 toolchain 生成后 `set(CMAKE_SYSTEM_NAME Linux CACHE STRING "" FORCE)`，
     或经 `CMakeToolchain` 变量注入。命令行 `-DCMAKE_SYSTEM_NAME=Linux` 会被工具链覆盖。

### P4. avahi 通过 pkg-config 查找失败
barrier 用 `pkg_check_modules(AVAHI_COMPAT REQUIRED avahi-compat-libdns_sd)`，
但 conan 的 avahi 配方未生成 `.pc`（仅暴露 cmake target）。
→ 需 patch `CMakeLists.txt:177`，GUI 分支改用它提供的 cmake target
  （`avahi-compat-libdns_sd::...` 或 find_package），或补 pkg-config 依赖。

### P5. Qt AUTOGEN 未识别版本
AUTOGEN 警告 "No valid Qt version found"：CMakeDeps 生成的 Qt5 需同时暴露
`Qt5::Core/Widgets/Network` 组件目标，且配方 `cmake_file_name=Qt5` 才被 find_package 捕获。

### P6. Version.cmake 报 `not a git repository`
配方 build() 在无 git 的源码目录里跑，版本号回落 00000000。
→ configure 需传 `-DBARRIER_REVISION=...` 或 `-DBARRIER_VERSION_STAGE=release`，不阻塞。

### P8. X11 头文件模块式查找失败
barrier 用 `check_include_files("X11/extensions/XTest.h" ...)` / `check_include_files("X11/XKBlib.h" ...)`
（模块式 Find 模块，非 target 模式），conan 的 X11 包头目录不会自动进入其查找路径。
→ 配方 generate() 需把依赖 include 目录注入 `CMAKE_REQUIRED_INCLUDES`/`CMAKE_INCLUDE_PATH`，
   （conan 头目录：libx11 -> .../p/libx1.../p/include，libxtst -> .../p/libxt.../p/include，
    avahi -> .../p/avahi.../p/include/avahi-compat-libdns_sd）。已在工作树找到：
    `X11/Xlib.h` 于 `~/.conan2/p/libx1*/p/include`，`XTest.h` 于 libxtst 包，
    `dns_sd.h` 于 avahi 包 include/avahi-compat-libdns_sd。

### P9. 依赖目录（conan cache 实测）
libx11=X11/、libxtst=、libxi=、libsm=、avahi-compat-libdns_sd=dns_sd.h（在 avahi pkg）
均需在配置阶段加入 include 搜索路径；库目录同理（`CMAKE_LIBRARY_PATH`）。

### P7. zlib 版本冲突（已解决）
`qt5-qtbase/5.15.2` 绑 `zlib/1.3.1`，`libcurl/8.5.0` 绑 `zlib/1.3.1.1`。
→ 配方 override `zlib/1.3.1`（与 qt5 预编译二进制一致），并把 libcurl 设为
   `shared=False, fPIC=True`（静态链接非-PIC 的 zlib/1.3.1，避开 shared 链接 PIC 报错）。

## 已 vendor 到工作树的文件（探索用）
- `ext/gulrak-filesystem/include/ghc/*.hpp`（gulrak/filesystem master）
- `ext/gtest/*`（google/googletest release-1.11.0 的 googletest 子目录）
- `ext/gmock/*`（同上，googlemock 子目录）

## 未决 / 下一步
1. P3/P4 是 configure 绿色通关的关键；P4 需 patch 上层 CMakeLists（固化入 conandata 补丁）。
2. 后续仍需处理编译期错误（-Werror、头文件、链接）与 ctest 运行结果。
### 对话 #1 — 依赖梳理与探索编译

- 从源码 CMakeLists.txt 核实真实依赖：GUI 用 Qt5（非 Qt6），核心硬依赖
  CURL/OpenSSL/Xtst/X11/dns_sd。
- ohpcd 制品核对：libcurl/8.5.0、openssl/1.1.1w、libxtst/6.1.0、libx11/6.4.0、
  libxi/6.1.0、avahi-compat-libdns_sd/0.9_rc5、libxext、libxfixes 均有 OHOS armv8 二进制。
- 三个 vendor 子模块（tarball 内为空）：gulrak-filesystem（ghc::filesystem）、
  googletest、googlemock。

### 对话 #2 — 编译适配（P1–P9）

- P1 cmake_minimum_required 3.4→3.5（CMake4 移除 <3.5）。
- P3 强制 CMAKE_SYSTEM_NAME=Linux：OHOS 无 CMake platform module，`if(UNIX)` 全失效。
- P4 avahi pkg_check_modules→find_package(CONFIG)。
- P3 补丁移除 pthread_setcancelstate/type（OHOS pthread.h 不声明）。
- 模块式 check_* 宏需注入 -I/-L；openssl include 用 CMAKE_CXX_FLAGS_INIT 注入。
- 探索 compile 暴露的哈希/链接错误逐个修复，最终 barriers/barrierc 编译链接成功。

### 对话 #3 — conan-verify 与 finish

- conan-verify G1–G4 全部通过；test_package `--version` 退出码为 3（kExitArgs，上游行为），
  改进 test.sh 改为断言输出（含 "Protocol version"）。
- prepatch 由 refresh-patch 重新生成（per-file difflib），conandata 同步引用新文件名。
- W3 本地 CI 模拟通过；junk_check 因分支提交后切换 incremental 仅扫本包文件。
- submit 就绪补齐：manifest 模板字段、test-report.md、packaging/ 产物、.staging-verified、README.md。
---

**编译结束**: 2026-09-01 12:24
**最终状态**: built
