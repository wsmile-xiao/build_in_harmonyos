# StratoHAL (libstrato)

ONScripter 系游戏引擎的**硬件抽象层（HAL）**，把引擎所需的平台能力收敛成一组
`hal_*` C API：图像解码（PNG / JPEG / WebP）、字形渲染（FreeType）、
音频（Ogg Vorbis / OpenSLES）、GL 渲染后端、平台文件 IO。

- 上游：<https://github.com/awemorris/StratoHAL>（Zlib 许可）
- 构建系统：CMake（`cmake_minimum_required(VERSION 3.18)`）
- 产物类型：共享库 `libstrato.so.1`（`package_type = library`，不带 CLI 工具，
  故软件级无 `commands.json`）

## 依赖

`libpng` / `libjpeg-turbo` / `libwebp` / `libogg` / `libvorbis` / `freetype` / `zlib`
——全部取自 ohpcd 制品仓预编译包（对应上游 `STRATO_ENABLE_DIST=ON` 的"用系统库"分支；
否则上游会从仓库自带 `lib/archive/*.tar.gz` 源码内联构建）。

## OHOS / HarmonyOS PC 适配要点

1. **上游确实声明了 OpenHarmony 目标**：`option(STRATO_TARGET_OPENHARMONY ...)`、
   `target_compile_definitions(... HAL_TARGET_OPENHARMONY)`、
   `target_link_libraries(strato PUBLIC m GLESv2 OpenSLES librawfile.z.so)`，
   并在该分支把源集切到 `image.c glyph.c wave.c glrender.c slsound.c ohmain.cpp ohfile.cpp`
   （`enable_language(CXX)`）。
2. 但 `cmake/toolchains/` 只有 ios/linux/macos/mingw/openwatcom/unity 共 17 个文件，
   **没有 openharmony** —— 交叉工具链必须在配方里自建。
3. 工具链关键点：OHOS 设备 `uname -s` 返回 `HarmonyOS`，而 CMake 不带
   `Platform/HarmonyOS.cmake` ⇒ 必须显式 `CMAKE_SYSTEM_NAME=Linux` 并给
   `CMAKE_SYSROOT` 与 OHOS clang 包装器。
4. 上游 `image.c`/`glyph.c`/`wave.c` 按其**自带** `lib/build-libs.sh` 的头文件布局
   写死 `#include <png/png.h>` / `<jpeg/jpeglib.h>`（子目录形式），而 conan 包的
   头文件是平铺的 ⇒ 需在 `build_folder` 建私有 include 前缀补齐子目录。
5. 上游 OHOS 目标的链接集合**不完整**（缺 EGL / GLESv3 / libhilog_ndk.z /
   libace_ndk.z / libace_napi.z，上游示例 App 是在 App 层补的）
   ⇒ 打成库包必须由库自身补齐，否则加载期报
   `Error relocating libstrato.so.1: <sym>: symbol not found`。
   其中 `glGenVertexArrays/glBindVertexArray/glDeleteVertexArrays`（核心 ES3 名）
   只在 `libGLESv3.so` 里 —— OHOS 的 `libGLESv2.so` 是单地址转发桩，只导出 OES 后缀名。
6. **消费者契约**：`ohmain.cpp` 以 `extern int VIEWPORT_WIDTH; extern int
   VIEWPORT_HEIGHT;` 引用视图尺寸，由消费者定义并导出（上游示例 App 在
   `resources/projects/openharmony/entry/src/main/cpp/napi_init.cpp` 定义为 1280x720）。

细节与验证记录见 [1.0.19/notes.md](1.0.19/notes.md)。
