# logstalgia 1.1.4 适配笔记（HarmonyOS PC / aarch64）

## 编译环境

- OS: HarmonyOS 6.0（OHOS PC，aarch64）
- Compiler: clang/clang++ 15（/data/service/hnp/bin）
- Conan: 2.x（OHOS 适配版 2.29.1，profile: ci/conan/profiles/ohos-aarch64）
- 构建日期: 2026-09-09

## 软件与上游核验

- 上游: https://github.com/acaudwell/Logstalgia（tag `logstalgia-1.1.4` 实证存在）
- 官方 release tarball: `releases/download/logstalgia-1.1.4/logstalgia-1.1.4.tar.gz`
  （sha256 `c049eff405e924035222edb26bcc6c7b5f00a08926abdb7b467e2449242790a9`）
- **关键决策：用 release tarball 而非 git tag 归档**。tag 归档（`archive/refs/tags/...`）
  不带 configure（需 autogen.sh + autoreconf）且缺 `src/core` submodule 内容；
  release tarball 是 `make dist` 产物，自带 configure / Makefile.in / aclocal.m4 /
  build-aux/config.guess|config.sub 与完整 src/core（acaudwell/Core@f7fa400），
  完全绕开 submodule 与 autoreconf（HMDFS 上 autoreconf 链有 E114 类冲突，见
  abiword-plugin-* 先例）。

## 构建方式

- 构建系统: Autotools（上游 configure + make）
- 编译命令: `./configure --build=aarch64-linux --host=aarch64-linux --with-boost=<pkg> --with-boost-system=boost_filesystem && make -j`
- 安装命令: `make install`（bin/logstalgia + share/logstalgia 数据文件）

## 依赖（全部制品仓已发布，W0 核验）

| 依赖 | conan 引用 | 说明 |
|------|-----------|------|
| SDL2 | sdl2/2.30.10 | 无 X11/Wayland，DUMMY/OFFSCREEN 驱动 |
| SDL2_image | sdl2-image/2.8.12 | PNG/JPG 加载（configure 检查 IMG_LoadPNG_RW/IMG_LoadJPG_RW 均过） |
| Boost | boost/1.84.0 | filesystem/regex/program_options/iostreams 静态库 |
| GLM | glm/0.9.9.8 | header-only |
| FreeType | freetype/2.14.3.1 | configure 要求 `freetype2 >= 9.0.3`（libtool 号 26.6.20） |
| PCRE2 | pcre2/10.45.1.1 | libpcre2-8 |
| libpng | libpng/1.6.58.2 | png_writer 用 |
| **gl4es** | gl4es/1.1.6 | 桌面 GL→GLES2 翻译层，提供 libGL.so + GL/gl.h|glext.h|glu.h |
| zlib | zlib/1.3.1.1 (override) | boost 要 1.3.1、libpng 闭包要 1.3.1.1，override 统一 |

## OHOS 图形栈适配方案（本配方核心）

OHOS PC 无桌面 OpenGL（仅 EGL + GLESv3）。logstalgia 依赖桌面 GL 固定管线 +
GLU + GLEW。方案（零上游源码补丁）：

1. **gl4es**（制品仓 gl4es/1.1.6）提供 `libGL.so`（桌面 GL 1.5/2.1 → GLES2 运行时
   翻译，含 FPE 固定管线模拟）与 `GL/gl.h`、`GL/glext.h`、`GL/glu.h` 头。
2. **GLU shim**（`compat/glu_glew_shim.cpp`）：gl4es 只带 GLU *声明*（libGL.so 无
   glu* 符号）。logstalgia 实际用 5 个 GLU 函数：`gluPerspective`（display.cpp:687）、
   `gluProject`（:734）、`gluUnProject`（:755）、`gluBuild2DMipmaps`（texture.cpp:232）、
   `gluErrorString`（gl.h 宏）+ configure conftest 的 `gluBeginCurve`。按 Mesa 公开
   域数学实现，编成 `libGLU.a`。
3. **GLEW shim**（`compat/include/GL/glew.h`）：Core 的 gl.h `#include <GL/glew.h>`。
   shim 转 include gl4es 头 + 定义 `GLEW_OK`/`GLEW_ERROR_NO_GLX_DISPLAY`/
   `GLEW_VERSION_2_0`（gl4es 目标桌面 GL 2.1，main.cpp:187 的
   `if(!GLEW_VERSION_2_0)` 分支不会误触发 ffp 回退）/ `GL_COMPUTE_SHADER`（GL 4.3
   常量，shader.cpp 引用但 logstalgia 不带 compute shader，运行时不触达）。
   `glewInit`/`glewGetErrorString`/`glewExperimental` 实现在 libGLU.a（C ABI）。
4. **configure 全走 pkg-config + 环境覆盖**，无源码补丁：
   - 配方在 PkgConfigDeps 输出目录生成别名 .pc：`gl`（→gl4es）、`glu`（→libGLU.a）、
     `glew`（→shim 头 + libGLU.a）、`freetype2`（→conan freetype，版本号写 libtool 号
     26.6.20 满足 `>= 9.0.3`）
   - PKG_CONFIG_PATH 注入 generators 目录
   - `--build/--host=aarch64-linux` 跳过 config.guess（OHOS 不被识别）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决 |
|---|------|------|------|
| 1 | zlib 版本冲突（boost 要 1.3.1，libpng 闭包要 1.3.1.1） | 制品仓二进制基于 1.3.1.1 | `self.requires("zlib/1.3.1.1", override=True)` |
| 2 | conftest "cannot run C++ compiled programs"（rc=77/127） | E467：AutotoolsDeps/依赖闭包进 conftest 链接，运行时缺 libc++_shared.so（SDK llvm/lib/aarch64-linux-ohos/c++）与依赖 .so | buildenv_info.append_path LD_LIBRARY_PATH 全量注入（依赖 libdirs + SDK c++ 目录） |
| 3 | GL 检查 `checking for GL... no` → `GL_LIBS=no` 传给 conftest | AX_CHECK_GL 的 PKG_CHECK_MODULES([GL],[gl]) 找不到 gl.pc，AC_SEARCH_LIBS 也找不到（无 -L 注入） | 造 gl.pc 指向 gl4es，让 pkg-config 路径直接成功 |
| 4 | GLU 检查同上 | 同 3 | 造 glu.pc 指向 libGLU.a shim |
| 5 | boostlib >= 1.46 检测失败 | ax_boost_base 默认扫系统路径 | `--with-boost=<boost package_folder>` |
| 6 | `Could not find a version of the Boost::System library` | boost_system 自 1.69 header-only，包内无 libboost_system.a，AC_CHECK_LIB 找不到 | `--with-boost-system=boost_filesystem`（AC_CHECK_LIB(x, exit) 对任何存在的库都过，exit 是 libc 符号） |
| 7 | glm/glm.h 检查失败 | AC_CHECK_HEADER 用 CPPFLAGS，glm 不在默认路径 | CPPFLAGS 注入 glm include |
| 8 | `pthread_setcancelstate` undeclared（boost smart_ptr） | OHOS musl 无此 API（已知平台差异） | `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`（boost 配方 cpp_info 也带，双保险显式注入） |
| 9 | `glBindBuffer` undeclared | gl4es 的 GL/gl.h 只到 GL 1.2 基线，VBO 等扩展原型在 glext.h 且需 `GL_GLEXT_PROTOTYPES` | shim glew.h 里先 `#define GL_GLEXT_PROTOTYPES 1` 再 include `GL/glext.h` |
| 10 | `GL_COMPUTE_SHADER` undeclared（shader.cpp） | 常量属 GL 4.3，gl4es glext.h 不含 | shim 补 `#define GL_COMPUTE_SHADER 0x91B9` |
| 11 | 运行时 `Error loading shared library libGL.so.1 ...` | conanrun 环境缺 gl4es libdir 与系统 EGL/GLES 路径 | test_package 注入 LD_LIBRARY_PATH（gl4es lib + /system/lib64）+ `LIBGL_GLES=/system/lib64/libGLESv3.so LIBGL_EGL=/system/lib64/libEGL.so`（gl4es test 同款） |
| 12 | `--version` 参数 segfault | 上游无 --version 参数（被当 log 文件路径）；`--help` 安全（parse 阶段打印后 exit(0)，不进渲染） | test 用 `--help` 不用 `--version` |

## 测试

- **GLU/GLEW shim 矩阵数学自测（双保险）**：`glu_glew_shim_selftest()`（无 GL
  上下文纯数学断言：恒等矩阵求逆、multiply_matrix 的 P*M 次序、gluProject/
  gluUnProject 往返）在两个位置运行——①主配方 `build()` 的 probe（步骤 1.5，
  链接 compat/lib/libGLU.a，gl4es 装载器初始化不可用的无头 worker 用 stub 满足
  静态链接）；②test_package/test.c（AI review PR #9643 接入消费者侧：主配方
  `package()` 现随包发布 libGLU.a，测试二进制链接它并最先跑 selftest，任何
  矩阵数学回归使消费者测试阶段直接失败）。
- test_package: test.c 用 `execlp("logstalgia", "logstalgia", "--help")`（fork+exec，
  绕过 OHOS mksh 无法 exec ELF 的限制——同旧 PR #2535 经验），由 bash 启动；
  运行环境注入 LIBGL_GLES/LIBGL_EGL + LD_LIBRARY_PATH=/system/lib64。
- **本机实测**（2026-09-09，OHOS PC + Maleoon 916 GPU）：`./logstalgia --help`
  打印完整帮助并 exit 0；gl4es 日志确认 `Using GLES 2.0 backend`、
  `Hardware Full NPOT detected and used`、`Hardware vendor is HUAWEI`、
  `LIBGL:loaded: /system/lib64/libGLESv3.so`、`/system/lib64/libEGL.so`——
  桌面 GL 栈在 OHOS 真实硬件初始化成功。
- 上游 `src/tests.cpp`（LogstalgiaTester，`--test` 选项）需真实图形环境
  （SDL2 窗口 + GL 上下文 + FreeType 字体渲染），无头 CI 不可执行，
  在 test_package/MANIFEST.yml 中如实声明。

## R40 图形渲染适配完整性说明

- logstalgia 的桌面 GL 调用（glBegin/glEnd/glVertex/glMatrixMode 等固定管线 +
  glCreateShader/glUseProgram 现代 shader 双路径）**经 gl4es 翻译层在 OHOS 真实
  EGL/GLES3 硬件上初始化成功**（--help 已实证 gl4es 完成 GLES 后端加载与硬件
  扩展探测：Full NPOT / FBO / BlendColor 等）。
- 完整渲染回路（创建 SDL 窗口 + 播放日志 + 逐帧绘制）需带显示器的设备交互验证，
  无头 CI 不可达；同链路先例：gl4es 离屏渲染自检（EGL pbuffer + 固定管线三角形 +
  glReadPixels 校验）与 assaultcube（SDL2 offscreen + gl4es）均已在同 GPU 跑通。
- 结论：编译通过 + GL 栈真实硬件初始化实证 + 同链路离屏渲染先例 → 基础适配
  完整；逐帧渲染的端到端验证留给有显示环境的使用方。

## 版本策略

- 首次适配，版本号 = 上游版本 `1.1.4`（R37）。
- 旧 PR #2535（他人弃子，作者 wangMing_Yuan，非本团队账号）用 `1.1.4-r3`
  非标准后缀；本任务按平台任务 #2654 从最新 main 重建，版本号规范回 1.1.4。
