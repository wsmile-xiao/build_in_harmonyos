# chromono 1.1.3 适配笔记

## 编译环境
- 构建系统: cmake（上游 min 3.27）
- 编译日期: 2026-09-08
- 编译器: clang/clang++（OHOS aarch64）
- 状态: built（2026-09-08 设备 conan create + test_package 实证 PASS）

## 编译步骤

1. 下载源码: https://github.com/mardy/chromono/archive/refs/tags/1.1.3.tar.gz
   （sha256 ae60b0de0b76790617ea258c4162d93545e5be319c7bc50ec514dfe2b3ad36ac）
2. 打补丁（配方 apply_conandata_patches）:
   - 0001: CMakeLists —— 默认 pkg-config/OpenGL 桌面分支前加 CHROMONO_OHOS_CONAN
     门控，走 CMakeDeps imported targets（sdl2::sdl2/Vorbis::vorbisfile/Ogg::ogg/
     zlib::zlib）+ -DUSE_OPENGL_ES；桌面路径保留 else()
   - 0002: main.cpp —— 加 --version 冒烟入口（先于任何 SDL/显示初始化）
   - 0003: main.cpp —— `#include <SDL.h>` 改 `<SDL2/SDL.h>`（ohpcd sdl2 头在 include/SDL2 下）
3. CMake 配置（配方 generate() 注入）:
   - CMAKE_SYSTEM_NAME=Linux / CMAKE_SYSTEM_PROCESSOR=aarch64（E092）
   - CMAKE_POLICY_VERSION_MINIMUM=3.5
   - CHROMONO_OHOS_CONAN=ON
4. 编译: cmake --build . --parallel 1（R9 规避 HMDFS mkfifo 坑）
5. 安装: cmake.install() → bin/chromono + share/applications/chromono.desktop
   + share/pixmaps/chromono.png；随后 llvm-objcopy 剥 .codesign +
   binary-sign-tool sign -selfSign 1 自签
6. 测试: 上游无测试（GUI 游戏）→ test_package：chromono --version 断言 +
   真实启动限时探测（GUI 验证边界）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游默认 CMake 分支硬编码 pkg-config + 桌面 OpenGL | OHOS 无 pkg-config 依赖发现/桌面 GL | 0001 patch：CHROMONO_OHOS_CONAN 门控走 CMakeDeps imported targets + ES 2.0 |
| 2 | 需 OpenGL ES 2.0 头/上下文 | chromono 同时支持桌面 GL 3.2 与 ES 2.0 | -DUSE_OPENGL_ES：`<GLES2/gl2.h>` + SDL ES2 context（main.cpp 原生支持） |
| 3 | CMake 不识别 HarmonyOS 平台 | OHOS 无对应 CMake 平台（E092） | CMAKE_SYSTEM_NAME=Linux + aarch64 |
| 4 | main() 无显示环境零容错 | SDL_CreateWindow 失败即空指针崩溃路径 | 不作为 gate；headless 验证改用 --version 冒烟入口（0002 patch） |
| 5 | 产物运行报 Operation not permitted | OHOS ELF 未签名 | llvm-objcopy --remove-section .codesign + binary-sign-tool sign -selfSign 1 |
| 6 | （潜在，worker CI）lld 加载 libxml2.so.16 失败 | CI worker 沙箱加载器 RUNPATH 问题 | build() 内 clang -print-resource-dir 推导 SDK llvm/lib 并注入 LD_LIBRARY_PATH（优雅降级，同 julius） |
| 7 | CMake: Target links SDL2::SDL2 but target not found | 我把链接目标写成上游 CMake 命名（SDL2::SDL2/ZLIB::ZLIB），但 ohpcd 配方经 CMakeDeps 导出的是小写 sdl2::sdl2/zlib::zlib | 0001 修正为 CMakeDeps 实测导出名（sdl2::sdl2 + zlib::zlib） |
| 8 | main.cpp: 'SDL.h' file not found | ohpcd sdl2/2.30.10 头文件装在 include/SDL2/ 下，配方导出的 include 根下无 SDL.h；其内部头全为引号相对 include，故只需改包含名 | 0003 patch：`#include <SDL2/SDL.h>` |

## 依赖版本

- sdl2 2.30.10（ohpcd 已发布，OHOS 静态核心库自带 ohaudio/native_window/EGL/GLESv2/m/pthread）
- libogg 1.3.6 + libvorbis 1.3.7（默认 shared；libvorbis 自带 libogg/1.3.6 require）
- zlib 1.3.1（static-only, R26）

## 验证结果

- **配方 SHA**（current = harmony = ci）: 876b71670a81eb78301f8e3fcd40b2eb0c4f94b2
- **Harmony verify（设备 conan create + test_package）**: PASS（2026-09-08）
  - 构建: 全源码编译 + 链接 + package（bin/chromono + desktop + png）+ objcopy 剥 .codesign + binary-sign-tool 自签
  - test_package: `chromono --version` → 'chromono 1.1.3'（可加载、共享依赖可解析、已自签）[pass]
  - 真实启动限时探测 → headless 边界（无显示/GLES2 上下文，rc=1），如实记录，非 gate
- **PR**: #8931（feat/chromono-1.1.3）
- **CI**: PASS
- **验证边界（GUI）**：chromono 是 SDL2/GLES2 图形游戏，main() 无显示环境零容错。
  headless CI 无法把真实主循环当 gate；test_package 用 --version（先于 SDL 初始化）
  证明"二进制可加载 + 共享依赖可解析 + ELF 已自签"，并对真实启动做限时探测：
  能进主循环即完整 GUI 冒烟通过；headless 下在显示/GL 初始化处退出则如实记录 GUI
  验证边界（非适配缺陷，不虚构成功）。建议在带显示/图形栈的 OHOS 环境人工确认
  渲染完整性。

## 注意事项

- chromono --version 为配方新增冒烟入口（0002 patch），正常游戏启动路径不受影响
- 运行时数据内嵌于二进制（packer.py → resources.cpp），无需外部数据目录
- XDG_CONFIG_HOME/HOME 决定存档位置（storagemanager），无该目录仅影响存档写入
