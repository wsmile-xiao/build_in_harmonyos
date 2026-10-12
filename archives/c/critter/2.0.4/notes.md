# critter 2.0.4 适配笔记

## 编译环境

- 构建系统: cmake（上游根 `Makefile` 是 emscripten 专用，Linux/OHOS 走 CMake）
- 编译日期: 2026-09-26
- 编译器: clang / clang++（ohos-sdk 26.0.0.18，`-stdlib=libc++`）
- 目标: OHOS / aarch64 / armv8 / musl / libc++
- Conan: 2.29.1（profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built（配方与产物已在本地完成 `conan create` 端到端验证；尚未经 release 流水线 `conan upload` 上传制品仓，故按归档规范记为 built 而非 published）

## 软件辨识（先做，避免重复适配）

`critter 1.0.2` 与已合入的 `criticalmass/1.0.2` **是同一个上游产物**：tar 包 sha256
同为 `846db2d30d39e559612328594084a7aef980169948b2cfaee9fddec8ffdef724`（5122126 B），
其 `Makefile.am` 里 `bin_PROGRAMS = critter`——即二者只是同一个 autotools 包在"包名"
上的两种叫法，制品仓里只有 `criticalmass/1.0.2`，`critter/*` 零命中。

因此本次适配对象改为 **mooflu/critter 2.0.4**（`https://github.com/mooflu/critter`），
它是 Critical Mass 的 **SDL2 + OpenGL 2.0 着色器**分支，与 1.x 的 autotools/SDL1
代码库完全不同源。版本号按 R37 用上游版本 `2.0.4`（首次适配，无适配修复后缀）。

## 编译步骤

```bash
export OHC_PROJECT_DIR=<worktree>          # 关键：否则 init-build 落到 SKILL 自带 archives
python3 $SKILL_ROOT/scripts/ohc-run.py init-build critter 2.0.4 \
    --url=https://github.com/mooflu/critter/archive/refs/tags/2.0.4.tar.gz
python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight critter 2.0.4 --src $BUILD_SRC_DIR
```

生成配方后，本地与 CI 同源验证命令：

```bash
conan create archives/c/critter/2.0.4 \
    -pr:h=./ci/conan/profiles/ohos-aarch64 -pr:b=./ci/conan/profiles/ohos-aarch64 \
    --build=critter/*
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake configure 阶段 `FATAL_ERROR "VERSION not specified or no git tag found"` | 根 `CMakeLists.txt` 用 `git describe --always --tags --abbrev=0` 推导 VERSION，而 GitHub 发布的源码 tarball 不带 git 元数据 | 显式传 `-DVERSION=${self.version}` |
| 2 | 找不到 `<glm/gtx/string_cast.hpp>`（`game/Particles.cpp`） | 根 `CMakeLists.txt` 追加 `-I${PROJECT_SOURCE_DIR}/3rdparty/glm`，但发布包**根本没有 `3rdparty/` 目录**（上游依赖本地 submodule/手工复制） | glm 走制品仓 `glm/0.9.9.8`，由配方的 include flags 提供 |
| 3 | C++ 源批量报 `use of undeclared identifier 'glGetUniformLocation' / glBindVertexArray / glGetStringi / glDebugMessageCallback'`；同一工程 `.c` 却能过 | gl4es 的 `GL/gl.h` 只在 `#if defined(__EMSCRIPTEN__) \|\| defined(__APPLE__)` 下 `#define GL_GLEXT_PROTOTYPES 1`（gl.h L30-33），而 `glext.h` 把 `GL_VERSION_2_0/2_1/3_0` 声明整段包在该宏内 → OHOS 上只暴露 GL 1.x 原型。C 源退化为隐式声明告警、C++ 是硬错误 | 下游 `compat/GL/glew.h`：在 `#include <GL/gl.h>` **之前**定义 `GL_GLEXT_PROTOTYPES`——gl.h L2097 无条件 include `glext.h`，宏已就位即让 2.0+/3.0 原型随 gl.h 一起可见。（**不能**反过来：放在 gl.h 之后靠二次 include `glext.h` 无效，`glext.h` 的 `__glext_h_` include guard 会把第二次 include 整个跳过。）沉淀为知识草稿 E702 |
| 4 | `find_package(GLEW REQUIRED)` 失败 / `cannot find -lGLEW` | OHOS 制品仓没有 glew 配方与二进制（`conan download glew/2.2.0 -r=ohpcd --only-recipe` → Recipe not found）；而工程实际只用到 3 个 GLEW 符号 + 一组 feature 宏 | `compat/glew-shim.c` 提供 GLEW 空实现（`glewInit` 返回 `GLEW_OK`、`glewGetString` 返回版本串）并归档为 `libGLEW.a`，CMake 侧 `-DGLEW_USE_STATIC_LIBS=ON` 命中 `GLEW::glew_s`。参考 `archives/l/logstalgia/1.1.4` |
| 5 | 链接期 `undefined reference to glDebugMessageCallback / glBindBufferBase / glProgramParameteri / glBindFragDataLocation` | gl4es 未导出这些入口（调试入口 + 少量 GL 3.x 入口）；引用它们的代码只存在于**从未被调用**的辅助类（`mooflu.common/utilsgl/gl3/Program.cpp`） | 在 shim 里补 no-op 空实现（不改变行为） |
| 6 | 链接期 `undefined reference to WebP*/TIFF*` | `libSDL2_image.a` 是**静态**库且编译进了 TIFF/WebP 支持，需要把后备库一起放进链接行 | 配方从依赖 prefix 里挑 `libwebp.so*` / `libwebpdemux.so*` / `libtiff.so*` 追加到 `SDL2_IMAGE_LIBRARY`（分号分隔列表） |
| 7 | cmake 找不到上游 `find_package(SDL2_image/SDL2_mixer/PhysFS)` 或读到 `NOTFOUND` | 上游用**自带 find-module**（`mooflu.common/utilscmake/`）配遗留变量（`SDL2_IMAGE_LIBRARY`、`PHYSFS_LIBRARY`…），而 CMakeDeps 只产出现代 IMPORTED target | configure 前显式 seed 全部遗留 cache 变量：`SDL2_LIBRARIES/SDL2_INCLUDE_DIRS/SDL2_IMAGE_LIBRARY/SDL2_MIXER_LIBRARY/PHYSFS_LIBRARY/PNG_LIBRARY/ZLIB_LIBRARY/OPENGL_LIBRARY` + 各自 `*_INCLUDE_DIR` |
| 8 | `find_package(OpenGL)` 去找 GLX/libGLX | OHOS 无桌面 GL / GLX，GL 栈由 gl4es 提供 | `-DOPENGL_gl_LIBRARY=<gl4es>/lib/libGL.so` + `-DOPENGL_INCLUDE_DIR=<gl4es>/include`（自带 include 目录，避免落到系统 GL 头） |
| 9 | `resource.dat` 不存在（cmake `add_executable` 需要它先存在） | 上游不把 `resource.dat` 打进发布包，由 `scripts/build-linux-no-oem.sh` 里 `zip -9r ../resource.dat .` 现打包 | 配方 `_write_resource_dat()` 在 configure 前按同样布局（顶层条目、无前导 `./`）打包 `data/`；并安装到 `bin/`（运行期 PhysFS 以 `./resource.dat` 相对工作目录挂载，必须与可执行文件同级） |
| 10 | 无 `install()` 规则，`conan create` 打不出产物 | 上游 `CMakeLists.txt` 完全没有安装规则 | `package()` 手工落 `bin/critter` + `bin/resource.dat` + `share/man/man6/critter.6` + `licenses/COPYING` |
| 11 | conan 注入的 `LD_LIBRARY_PATH` 在构建脚本里失效 | OHOS 的 `/bin/sh` 是 mksh 且会**重置 `LD_LIBRARY_PATH`**，导致 loader 报 `Error loading shared library libc++_shared.so` | 全部 `self.run(..., env="conanbuild")`，由 profile 的 `CONFIG_SHELL`/`SHELL=/data/service/hnp/bin/bash` 走 bash |
| 12 | zlib 版本菱形（`Conflict between zlib/1.3.2 and zlib/1.3.1.1`，源自 `libpng/1.6.58.3` 与 `libtiff/4.7.2`） | 依赖链上 libpng/libtiff 对 zlib 的下限不一致 | 直接 `self.requires("zlib/1.3.1.1")` 与 `libpng/1.6.58` 对齐（沿用 `criticalmass/1.0.2` 的钉法），并在运行期用 banner 复核（`zlib Version 1.3.1`、`PNG Version 1.6.58`） |
| 13 | gl4es 以 `LIBGL: Initialising gl4es` 后 `SIGSEGV`（rc=139） | gl4es 通过 `dlopen` 加载 EGL/GLES 后端，未提供 `LIBGL_GLES`/`LIBGL_EGL` 时后端为空 | `package_info()` 导出 `LIBGL_GLES=/system/lib64/libGLESv3.so`、`LIBGL_EGL=/system/lib64/libEGL.so`（同 `gl4es` 自带 test_package 与 `logstalgia/1.1.4`） |

## 源码修改

**无对上游源码的修改**（`patches_applied: []`）。全部适配都以"下游附加物"形式落在
配方内：

- `compat/GL/glew.h` — GLEW/GL 原型补齐头（`exports_sources` 携带）
- `compat/glew-shim.c` — GLEW 入口 + gl4es 未导出符号的空实现，编成 `libGLEW.a`

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| zlib | 1.3.1.1 | 直接依赖（`main.cpp` 打印 `zlibVersion()`，`CMakeLists` 链 `${ZLIB_LIBRARY}`）；与 libpng/libdtiff 系列对齐消解菱形 |
| libpng | 1.6.58 | 直接依赖 |
| sdl2 | 2.30.10 | 直接依赖（窗口/输入） |
| sdl2-image | 2.8.12 | 直接依赖（静态库，需显式追加 WebP/TIFF 后备库） |
| sdl2-mixer | 2.8.2 | 直接依赖（音频） |
| physfs | 3.2.0.1 | 直接依赖（`resource.dat` 挂载） |
| gl4es | 1.1.6 | OHOS GL 栈（`libGL.so`） |
| glm | 0.9.9.8 | 上游发布包缺 `3rdparty/glm`，改走制品仓 |
| libwebp / libtiff / libjpeg-turbo / xz / zstd | 1.6.0 / 4.7.2 / 3.2.0 / 5.6.2 / 1.5.7 | 传递依赖（静态 `libSDL2_image.a` 的后备库） |

## 验证结果

```bash
$ conan create archives/c/critter/2.0.4 \
      -pr:h=./ci/conan/profiles/ohos-aarch64 -pr:b=./ci/conan/profiles/ohos-aarch64 \
      --build=critter/*
...
critter/2.0.4 (test package): [case] packaged-layout
critter/2.0.4 (test package): [case] elf-ohos-aarch64
critter/2.0.4 (test package): [case] resource-bundle
critter/2.0.4 (test package): [case] runenv-contract
critter/2.0.4 (test package): [case] dep-versions-reported
critter/2.0.4 (test package): [test] critter/2.0.4 消费者校验：6 用例、27 项断言，通过 27、失败 0
critter/2.0.4 (test package): HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, ...,
  "discovered": 6, "passedCount": 6, "assertions": 27, "assertionsPassed": 27}
```

运行期（主机 aarch64 即 OHOS 目标 ABI，gl4es GLES 后端）实测日志：

```text
INFO: Critter 2.0.4 - 23:52:44 Sep 26 2026
INFO: Copyright (C) 2004-2023 by Frank Becker
INFO: Visit http://games.mooflu.com
LIBGL: Initialising gl4es
LIBGL: GLES 2.0 backend
INFO: Search Paths:
INFO: ./resource.dat
INFO: Write Dir:.../.critter/
INFO: Cleanup complete. Ready to Exit.
LIBGL: Shutting down
```

产物：`bin/critter` — `ELF64 LSB AArch64`（`e_machine=183`）、`ET_DYN`(PIE)、
`PT_INTERP=/lib/ld-musl-aarch64.so.1`。

**在无头环境下的驱动器选择**（测试相关，重要）：`SDL_VIDEODRIVER=none` 在缺少
gl4es 后端变量时会 `SIGSEGV`；即使补上后端变量，其耗时统计也会出现异常值。测试
统一使用 `SDL_VIDEODRIVER=invalid`（走 SDL 的失败分支、稳定返回 rc=0、不挂死），
配合配方导出的 `LIBGL_*` 完成 gl4es 初始化/关闭的端到端验证。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/critter` | 2824832 B | 游戏主程序（AArch64 PIE） |
| `bin/resource.dat` | 5524754 B | 资源包（214 个顶层条目，PhysFS 以 `./resource.dat` 挂载） |
| `share/man/man6/critter.6` | — | 用户手册 |
| `licenses/COPYING` | — | GPL-2.0-only |

## 注意事项

- **无 `--version`/`--help`**：上游 CLI 解析器（`Config::updateFromCommandLine`）只有
  `+keyword value` / `-keyword value` / `-keyword` 形式，**没有版本开关**。因此测试
  不能沿用 `test_package-executable` 模板的 `--version` 冒烟，改为断言运行期横幅
  `Critter 2.0.4`（日志走 `Trace::Log` → `cout`；若定义 `TRACE` 则落 `trace.txt`）。
- **无头环境**：不可进入主循环，测试只验证"初始化 → 资源挂载 → 正常退出"路径；
  真实渲染/输入需在带显示的设备上人工验证。
- **GLEW 版本串**：shim 的 `glewGetString` 返回的是兼容版本串，不代表真实硬件能力；
  若后续有包依赖 GLEW 做能力探测，需按 gl4es 实际能力复核。
- **resource.dat 与可执行文件必须同目录**：上游以工作目录相对的 `./resource.dat`
  经 PhysFS 挂载，拆开会导致资源挂载失败并回落读 `data/` 目录。
- **配方形态对齐仓库模板**：用 `def export_sources()` 方法（而非 `exports_sources`
  属性）声明 `compat/` 两个文件，并在 `source()` 末尾调用 `apply_conandata_patches(self)`。
  本包当前**不需要任何补丁**（`patches_applied: []`），该调用在 conandata.yml 无
  `patches:` 段时是带 info 的**无操作**；之所以保留，是因为 conan-verify 的 G1 门禁按
  仓库模板做字面量校验，且同类已合入配方（`archives/f/fceux/2.6.6`、`archives/c/criticalmass/1.0.2`）
  同样是"无补丁段 + 保留该调用"的形态，未来若要加适配补丁只需往 conandata.yml 补条目。
- **W3/zsh 环境坑（会伪装成 CI 失败）**：本平台 `/tmp` 只读，而 zsh 的
  here-document 落盘位置由 `TMPPREFIX`（默认 `/tmp/zsh`）决定、**不看 `TMPDIR`** →
  直接跑 `ci/conan/build_and_test.sh` 会在 L0i/L0m 报
  `can't create temp file for here document: read-only file system`，
  看起来像 CI 脚本缺陷其实是环境问题。先 `export TMPPREFIX=$HOME/tmp/zsh` 再跑即可通过。
---

**编译结束**: 2026-09-27 00:33
**最终状态**: built
