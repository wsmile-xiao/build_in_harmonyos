# critter

> 俯视角街机射击游戏，Critical Mass 的 SDL2/OpenGL 分支，2.0.4（GPL-2.0-only）。

## 简介

Critter 是 Frank Becker 维护的俯视角射击游戏，为 Critical Mass 的 SDL2 移植分支，
2.0.4 由 mooflu 维护（`mooflu/critter`）。上游构建为 CMake（根目录 Makefile 仅服务
Emscripten 目标），图形走 OpenGL 2.0 着色器管线，音视频/输入走 SDL2，
资源以 PhysFS 打包读取。

> **与 `criticalmass/1.0.2` 的关系**：两者是**不同代码库**。`criticalmass` 是 autotools
> + SDL1 的原始分支，`critter` 是 SDL2 + GL2 着色器管线的新分支。
> 注意历史归档中所谓 "critter 1.0.2" 实为 `criticalmass` 1.0.2 的产物
> （同一 tar 包，sha256 `846db2d3…`，包内 `bin_PROGRAMS = critter`），
> 直接按该名字重复适配会与已合入的 `criticalmass/1.0.2` 撞车。

## OHOS 适配要点

- CMake 构建的 SDL2 图形应用包（application 类型），产物为 `bin/critter` 与
  同目录 `bin/resource.dat`；因含可执行文件，软件级 `commands.json` 已声明（R38）。
- **上游无任何 `install()` 规则**，`conan create` 打不出产物，`package()` 手工落
  `bin/`（含 `resource.dat`）、`share/man/man6/`、`licenses/`；`package_info()` 的
  `includedirs`/`libdirs` 为空，`bindirs=["bin"]`。
- **VERSION 必须显式注入**：根 `CMakeLists.txt` 用
  `git describe --always --tags --abbrev=0` 取版本并在取不到时 `FATAL_ERROR`，
  而发布 tarball 不带 git 元数据 → 配方传 `-DVERSION=2.0.4`。
- **`3rdparty/glm` 不在发布包里**：根 `CMakeLists.txt` 追加
  `-I${PROJECT_SOURCE_DIR}/3rdparty/glm`，但 tarball 无 `3rdparty/` 目录
  （`game/Particles.cpp` 用 `glm/gtx/string_cast.hpp`）→ glm 走制品仓 `glm/0.9.9.8`。
- **GL/GLEW 面用下游 compat shim 补齐**（同 `logstalgia/1.1.4` 思路）：
  OHOS 既无 GLEW 也无桌面 GL，GL 栈为 `gl4es/1.1.6`。配方自带
  `compat/GL/glew.h` + `compat/glew-shim.c`，编成静态 `libGLEW.a`，
  经 `GLEW_USE_STATIC_LIBS=ON` → `GLEW::glew_s` 被 CMake 的 `FindGLEW` 命中。
  - `compat/GL/glew.h` 在 `#include <GL/gl.h>` **之前**定义 `GL_GLEXT_PROTOTYPES`：
    gl4es 的 `gl.h` 只对 Emscripten/Apple 定义该宏，而 `gl.h` 会无条件 include
    `glext.h`（其 2.0+/3.0 原型块由该宏门控），故"先定义"即让原型可见。
    反过来放在 `gl.h` 之后靠二次 include 补救是无效的（`__glext_h_` guard 会跳过）。
  - `glew-shim.c` 以空实现补 `glewInit()`/`glewGetString()`/`glewExperimental`，
    以及 gl4es 未导出的 `glDebugMessageCallback`/`glDebugMessageControl` 与
    `glBindBufferBase`/`glProgramParameteri`/`glBindFragDataLocation`
    （仅被工程中**未被调用**的辅助代码引用）。
- **`resource.dat` 构建期打包**：上游由 `scripts/build-linux-no-oem.sh` 用 `zip -9r data/`
  生成，tarball 里没有；而 CMake `add_executable` 需要它先存在、运行期又由
  PhysFS 以工作目录相对路径 `./resource.dat` 挂载 → 配方在 `build()` 里打包并随
  `bin/` 安装，保证与可执行文件同目录。
- **运行期必须导出 gl4es 后端变量**：gl4es 以 `dlopen` 方式加载 EGL/GLES，
  `package_info()` 导出 `LIBGL_GLES=/system/lib64/libGLESv3.so`、
  `LIBGL_EGL=/system/lib64/libEGL.so`；缺任一个会直接 `SIGSEGV`
  （`LIBGL: Initialising gl4es` 后崩溃）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| zlib | 1.3.1.1 | 直接依赖（`game/main.cpp` 打印 `zlibVersion()`，并链接 `${ZLIB_LIBRARY}`）；同版本号统一 `libtiff` 侧的 zlib 下限 |
| libpng | 1.6.58 | 上游 `find_package(PNG REQUIRED)`；与 `libtiff/4.7.2` 一起收敛到 zlib/1.3.1.1（同 `criticalmass/1.0.2` 的 pin） |
| sdl2 | 2.30.10 | 窗口/输入/音频与 OpenGL 上下文 |
| sdl2-image | 2.8.12 | PNG 贴图加载；静态链接需显式带上 WebP/TIFF 传递库 |
| sdl2-mixer | 2.8.2 | 音效与音乐 |
| physfs | 3.2.0.1 | `resource.dat` 资源包挂载（上游 `find_package(PhysFS REQUIRED)`） |
| gl4es | 1.1.6 | OHOS 上的桌面 GL → GLES 转译层（提供 `libGL.so`） |
| glm | 0.9.9.8 | 头文件库；替代上游缺失的 `3rdparty/glm` |
| libtiff / libwebp / libjpeg-turbo / xz / zstd | 传递依赖 | 由 libpng、sdl2-image 带入，无需显式声明 |

## 功能验证

```bash
# 运行期需要 gl4es 后端变量（package_info 已导出，conanrun 环境自动带上）
LIBGL_GLES=/system/lib64/libGLESv3.so \
LIBGL_EGL=/system/lib64/libEGL.so \
SDL_VIDEODRIVER=invalid ./critter
```

期望输出（stdout 横幅，critter 无 `--version` 参数，故以启动横幅为冒烟判据）：

```
INFO: Critter 2.0.4 - <构建时间>
INFO: Copyright (C) 2004-2023 by Frank Becker
INFO: Visit http://games.mooflu.com
...
INFO: Cleanup complete. Ready to Exit.
```

无头环境下 `SDL_VIDEODRIVER=invalid` 可在初始化失败前确定性退出（`none` 需依赖
gl4es 后端变量，裸跑则会 `SIGSEGV`）。`test_package/` 另断言产物布局、
ELF 机器字（AArch64）、`resource.dat` 存在与内容、`bin/critter` 的 NEEDED 依赖表
与依赖版本一致性（共 6 个用例 / 27 条断言）。

## 参考

- [上游仓库](https://github.com/mooflu/critter)
- [官网](https://games.mooflu.com/)
- [Linux 构建脚本](https://github.com/mooflu/critter/blob/master/scripts/build-linux-no-oem.sh)
- 相关归档：`archives/c/criticalmass/1.0.2`（同源上游另一分支）、
  `archives/l/logstalgia/1.1.4`（GLEW 头 shim + 静态 shim 库先例）
