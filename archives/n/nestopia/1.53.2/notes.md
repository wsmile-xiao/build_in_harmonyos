# Nestopia 1.53.2 — HarmonyOS PC 适配笔记

## 概述

上游 nestopia 1.53.2（GPL-2.0）的 Unix 构建产物是 `nestopia` FLTK GUI
模拟器，由三部分组成：

- `source/core/` — 模拟器核心（Nes::Core::Api::*），**无显示依赖**
- `source/nes_ntsc/` — 仅头文件的 NTSC 滤镜
- `source/fltkui/` — FLTK 前端（`main()` 所在）；SDL2 仅用于输入

## 关键决策与埋点

### 1. 构建系统：autotools + autoreconf
tarball 不含 `configure`，只有 `configure.ac`/`Makefile.am`，因此
`build()` 先执行 `autoreconf -fi`。宏依赖：
- `AC_INIT`/`AM_INIT_AUTOMAKE` → autoconf + automake
- `AX_*` 系列宏（AX_CHECK_ENABLE_DEBUG、AX_COMPILER_VENDOR、
  AX_CXX_COMPILE_STDCXX([17]) 等）→ **autoconf-archive**

tool_requires：
- `autoconf/2.72`
- `automake/1.18`
- `autoconf-archive/2024.10.16`

CI 为远端干净环境，无系统 automake/autoconf，必须走 tool_requires
（pdfsandwich 先例）。

### 2. 交叉/混合环境 flags 隔离（patches/0001）
configure.ac 原始写法用 `PKG_CHECK_MODULES`（zlib/libarchive/samplerate/
sdl2/epoxy）和 `fltk-config`（FLTK）探测依赖。这些探测在 OHOS 构建环境
会返回宿主机 native flags（交叉污染）或根本找不到 conan 包（fltk-config
不在 PATH）。patch 0001 将全部依赖探测改为 **外部显式传入
`*_CFLAGS`/`*_LIBS`，未设置直接 AC_MSG_ERROR**，彻底不依赖
pkg-config/fltk-config 探测（也就不需要 pkg.m4）。conanfile 的
generate() 依据 `self.dependencies[*].cpp_info`（含 components）组装绝对
路径 flags，通过环境变量注入 configure。

### 3. FLTK GL 缺口的处理（patches/0002 + 0003）
OHOS SDK 提供 EGL/GLES2（`libEGL.so`/`libGLESv2.so`），**没有 GLX/桌面
OpenGL**。仓内 `libfltk/1.3.11` 配方以 `OPTION_USE_GL=OFF` 构建，因此
不产出 `libfltk_gl.a`（已实证：包内无该库，`nm -u` 亦无 Fl_Gl_Window
符号）。而 nestopia 前端 `NstGlArea : public Fl_Gl_Window` 必须链接这些
符号。

- patch 0002：把新增源文件 `source/fltkui/fltkui_gl_ohos.cpp` 加入
  `nestopia_SOURCES`。
- patch 0003：新增该文件，提供 Fl_Gl_Window 全部符号（构造/析构/
  show/flush/handle/draw/make_current/swap_buffers/can_do 等），其中
  `can_do()` 诚实地返回 0 —— 声明 OHOS 无法创建 GLX 上下文，窗口退化
  为基类 Fl_Window 行为。**保持上游链接契约完整**，GUI 在无头/无 GLX
  环境不可运行，已如实写入 PR 描述。

### 4. 无头核心测试（libnestopia_core.a）
core 仅依赖 zlib（`NstZlib.cpp` include `zlib.h`），无显示/前端依赖。
`build()` 在 `make` 后把 `build_folder/source/core/**/*.o` 归档为
`libnestopia_core.a` 并随包安装 `include/nestopia/`（保留 api/board/
input/vssystem 子目录）。test_package 链接该库 + zlib，加载程序化生成的
最小 iNES ROM，跑帧断言，全程不碰 FLTK/SDL/GL。

### 5. 链接细节
- FLTK 1.3 自带图像编解码（libfltk_jpeg/png/z），配方 package_info 只
  声明 fltk_images+fltk，需按依赖序补 `-lfltk_jpeg -lfltk_png -lfltk_z`。
- FLTK 链接 `-lfltk_gl` 由 stub 取代（stub 编进 nestopia 可执行文件本身，
  无需单独库）。
- SDL2 静态库需 OHOS system_libs（ohaudio/native_window/EGL/GLESv2/m/
  pthread），从 sdl2 组件 cpp_info 自动取。
- libx11 为 shared `libX11.so`，由 libfltk 依赖链带入。

## 复用参考
- `archives/l/libarchive/3.8.7/conanfile.py` — autotools 流程骨架
- `archives/s/SDL2/2.32.10/conanfile.py` — OHOS system libs 处理
- `archives/m/mt32emu/2.7.1/` — 模拟器核心八件套/签名/test_package 结构