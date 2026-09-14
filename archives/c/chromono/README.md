# chro.mono (chromono)

chro.mono 是 Thomas Perl（thp）在 2013 年发布的圆形配色益智游戏的开源版
（https://thp.io/2013/chromono/），纯 C++17 / CMake，GPL-2.0-or-later。
本仓适配上游发布版 **1.1.3**（2026-01，含 Wii 移植与 GCC 15 / Debian 打包修复）。
单一可执行文件；游戏数据（图片/标记/着色器/音效）在构建期由 packer.py 内嵌进
二进制（resources.cpp），运行时无需外部数据目录。

## OHOS 适配要点

- 上游默认 CMake 分支硬编码 pkg-config + 桌面 OpenGL（`find_package(OpenGL)`）。
  用 CMake patch 增加 `CHROMONO_OHOS_CONAN` 门控分支：改走 Conan CMakeDeps
  imported targets（`sdl2::sdl2` / `Vorbis::vorbisfile` / `Ogg::ogg` /
  `zlib::zlib`——以 CMakeDeps 实测导出名为准，非上游大写命名），并
  `-DUSE_OPENGL_ES` 走 OpenGL ES 2.0（main.cpp 原生支持 ES 2.0 context，渲染仅
  GLES2 gl* 直调）；桌面 pkg-config/OpenGL 路径保留在 else()。
- ohpcd sdl2/2.30.10 把头文件装在 `include/SDL2/`（导出根下无 SDL.h），故 main.cpp
  用 `#include <SDL2/SDL.h>`。
- E092：`CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`；
  `CMAKE_POLICY_VERSION_MINIMUM=3.5`；构建 `--parallel 1` 规避 HMDFS mkfifo 坑。
- 依赖（均已在 ohpcd 发布）：sdl2/2.30.10、libogg/1.3.6、libvorbis/1.3.7（默认
  shared）、zlib/1.3.1（static-only）。
- `bin/chromono` 用 binary-sign-tool 自签（OHOS ELF 必需）。
- **验证边界（GUI）**：chromono 是 SDL2/GLES2 图形游戏，main() 对无显示环境零容错
  （SDL_CreateWindow 失败即走空指针路径）。headless CI 无法把真实游戏主循环当
  gate；配方新增最小 `--version` 冒烟入口（先于任何 SDL/显示初始化，纯增量、不碰
  渲染路径），test_package 用其证明"二进制可加载 + 共享依赖可解析 + ELF 已自签"，
  并对真实启动做限时探测记录 GUI 验证边界。**SDL2/GLES2 渲染与游戏主循环在 OHOS
  上的实际运行未在 CI 验证**——建议在带显示/图形栈的 OHOS 环境人工确认适配完整性。

## 依赖关系

- 构建/运行依赖：sdl2/2.30.10、libogg/1.3.6、libvorbis/1.3.7、zlib/1.3.1
  （已发布到 ohpcd）

## 参考资料

- 上游主页：https://thp.io/2013/chromono/
- 上游源码：https://github.com/mardy/chromono（1.1.3 tag）
- 上游构建依赖：README 内 DEPENDENCIES（SDL 2.0.10+、libvorbisfile、zlib、CMake 3.27）
