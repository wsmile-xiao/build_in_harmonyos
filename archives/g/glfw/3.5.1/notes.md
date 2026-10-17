# glfw 3.5.1 编译笔记（HarmonyOS PC · Conan cmake · Null-only 方案）

## 定位
- 源码：**上游原版** GLFW 3.5.1 官方 release zip（GitHub releases，非 ohos_native_glfw fork）。
- 方案：**Null-only 后端**——上游 3.5.x 将 Null 平台源码（_init/monitor/window/joystick.c）无条件编入
  核心库，关闭 X11/Wayland 后即得一个纯无头 GLFW，`glfwInitHint(GLFW_PLATFORM, GLFW_PLATFORM_NULL)`
  即可用。产物 `libglfw.so.3.5`（soname `libglfw.so.3`）+ glfw3.pc + glfw3Config.cmake。
- 与 3.4.6（ohos fork XComponent 桥接）不同：上游核心库**无循环依赖**，不需要 two-pass/bridge，
  单次 cmake 即可。

## 关键适配
1. **posix_time.c 补丁**（复用 3.4 的 0001 补丁，3.5.1 行号上下文仍匹配）：
   `#include <time.h>`——musl + 上游 `C_EXTENSIONS OFF`/`C_STANDARD 99` 严格 c99 下不暴露
   `clock_gettime`/`CLOCK_REALTIME`/`CLOCK_MONOTONIC`（E152）。
2. **`-D_DEFAULT_SOURCE` 编译宏**：上游 src/CMakeLists.txt 仅在 `CMAKE_SYSTEM_NAME == "Linux"`
   时给 glfw 目标加 `_DEFAULT_SOURCE`（Linux 上 -std=c99 关闭 _DEFAULT_SOURCE 的 workaround），
   OHOS toolchain 下 SYSTEM_NAME=OHOS 不命中该分支，posix_time.c 仍缺常量 → 通过
   `CMAKE_C_FLAGS=-D_DEFAULT_SOURCE` 注入（仅补丁还不够——3.5.1 比 3.4 多了此坑，
   3.4 notes 里 `-DCMAKE_C_FLAGS="-D_GNU_SOURCE"` 同因）。
3. **OHOS toolchain 自发现**（底稿自 3.4.6 `_ohos_toolchain()`，裁掉 two-pass）：
   不用 conan 生成的 conan_toolchain.cmake（os=OHOS 退化成未知平台 HarmonyOS、不出 SONAME），
   直接用 NDK 的 `ohos.toolchain.cmake`（CMAKE_SYSTEM_NAME=OHOS → SONAME/版本软链齐）。
   发现顺序：profile [conf] user_toolchain → `OHOS_NDK_HOME` → glob `/data/service/hnp/ohos-sdk.org/*`。
   CI 裸跑可复现（不依赖 profile host 段）。
4. **CMake 开关矩阵**：`GLFW_BUILD_X11=OFF GLFW_BUILD_WAYLAND=OFF`（ohos.toolchain 下 UNIX=1，
   不显式关会双关 X11/Wayland → find_package(X11 REQUIRED) FATAL_ERROR）；examples/tests/docs 全 OFF。
5. **平台选择逻辑验证**（3.5 新平台机制）：X11/Wayland 全关后 `supportedPlatforms[]` 为空数组，
   仅显式 `GLFW_PLATFORM_NULL` 可连接 null 后端（`_glfwSelectPlatform` 实测）。
6. **`-Wl,--undefined-version`**：lld 对无版本节 soname 的兼容（保险注入，3.4.6 未需要，3.5.1 实测无害）。

## EGL/GLES 说明（编译宏可选注入，本配方未启用）
上游 `egl_context.c` 在 OHOS（非 OpenBSD/NetBSD）默认找 `libEGL.so.1`/`libGLESv2.so.2`
（带版本号 soname），OHOS 系统库是无版本号的 `libEGL.so`/`libGLESv2.so`。运行期按需 dlopen，
Null-only 包不链接 EGL/GLES（DT_NEEDED 仅 libc.so），故**本配方不注入** `_GLFW_EGL_LIBRARY`/
`_GLFW_GLESV2_LIBRARY` 宏——需要 EGL 上下文的下游用户如遇 soname 不匹配可后续加选项。
（编译验证：libglfw.so.3.5 的 NEEDED 只有 libc.so）

## 系统库
`system_libs = ['m', 'pthread', 'rt', 'dl']`（上游 pkg-config Libs.private: -lrt -lm -ldl +
Threads::Threads；实测 NEEDED 仅 libc.so，musl 全并入 libc，声明保留语义完整）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `use of undeclared identifier 'CLOCK_REALTIME/CLOCK_MONOTONIC'` | musl + 严格 c99 隐藏 POSIX 定时器常量（E152），且 OHOS 下上游 `_DEFAULT_SOURCE` workaround 不生效（仅 Linux 分支） | 补丁加 `#include <time.h>` + `CMAKE_C_FLAGS=-D_DEFAULT_SOURCE` |
| 2 | conan create 时 cmake 报 `Error loading shared library libc++_shared.so` | 本机 OpenDesk 会话 LD_LIBRARY_PATH 含 `/data/storage/el1/bundle/libs/arm64`（bundle 版 libc++_shared.so 与 hnp cmake 不兼容，musl 优先取 LD_LIBRARY_PATH） | 本地会话过滤 bundle 段后跑 conan（CI 环境无此段，不受影响） |
| 3 | test_package `glfwCreateWindow(GLFW_NO_API)` 报 `OSMesa: Library not found` | `GLFW_NO_API` 是 window hint 不是 createWindow 参数，未设置 `glfwWindowHint(GLFW_CLIENT_API, GLFW_NO_API)` 时默认 OpenGL → null 平台尝试加载 OSMesa | 测试中先 `glfwWindowHint(GLFW_CLIENT_API, GLFW_NO_API)` |
| 4 | test 假设 null 平台无监视器（GetMonitors==NULL） | 上游 null 平台 `_glfwPollMonitorsNull` 实际模拟一个假监视器 "Null SuperNoop 0"（1920x1080@60，伽马 256 项） | 断言改为完整监视器 API 验证（count==1、名字、位置、缩放、视频模式、伽马） |

## 测试（N 申报口径：上游 20 个测试程序，build-only 验编译）
- 上游 `tests/CMakeLists.txt` 有 **20 个 `add_executable`**（allocator/clipboard/events/msaa/glfwinfo/
  iconify/monitors/reopen/cursor/empty/gamma/icon/inputlag/joysticks/tearing/threads/timeout/title/
  triangle-vulkan/window），**无 `add_test`/`enable_testing`**——非 CTest 体系，且全部需要真实
  窗口系统/显示器/GL/Vulkan 才能运行。主配方 `GLFW_BUILD_TESTS=OFF`，按 build-only 口径申报。
- test_package 自写 **NULL 平台生命周期测试（21 断言，无头真跑）**：glfwInitHint(NULL 平台)→
  glfwInit→版本 3.5.1→glfwWindowHint(NO_API)+CreateWindow(640x480)→窗口尺寸回读→监视器 API 全链路
  （模拟监视器 GetMonitors/GetPrimaryMonitor/Name/Pos/ContentScale/VideoMode 1920x1080@60/GammaRamp）→
  输入 API（Set/GetInputMode、GetKey）→剪贴板→时间 API（posix timer）→标题/shouldClose→Destroy→
  Terminate。实测输出 `ALL 21 CHECKS PASSED`。
- GL 实渲染验证为平台限制：OHOS 系统 EGL pbuffer 限 1×1（egl/1.0.5 先例实证），PR 正文按此口径豁免说明。

## 验证结果
- conan create（ci/conan/profiles/ohos-aarch64，shared=True）：exit 0，test_package 21/21 断言通过。
- conan-verify：G0/G2/G3/L2/L4/L5 全 PASS。
- 产物：libglfw.so.3.5（SONAME libglfw.so.3，NEEDED 仅 libc.so）+ include/GLFW/{glfw3.h,glfw3native.h}
  + lib/cmake/glfw3/* + lib/pkgconfig/glfw3.pc（Version: 3.5.1）。

## 编译日期
2026-09-06
---

**编译结束**: 2026-09-06 20:21
**最终状态**: published
