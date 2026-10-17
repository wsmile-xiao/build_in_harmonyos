# E702（草稿/预留编号）：OHOS 上 gl4es 缺失 GL 2.0+/3.0 原型声明，`<GL/glew.h>` 工程批量报「未声明标识符」

> Status: DRAFT（预留条目 **E702**）
> Source: critter 2.0.4（mooflu/critter，SDL2 分支）HarmonyOS PC 适配，2026-09-26
> Related: E013 / E019（dlopen 面，与本条正交）、`archives/l/logstalgia/1.1.4`（同类头 shim 先例）

## 背景

critter 2.0.4 是一个使用 OpenGL 2.0+ 着色器管线的 SDL2 游戏（约 19 处
`#include <GL/glew.h>`）。在 OHOS 上按常规方式接入 gl4es（`libGL.so`）后，CMake
配置能过、SDL2/libpng/physfs 等依赖都能解析，但**编译期在 C++ 源文件上批量报
「use of undeclared identifier」**，指向的全是 GL 2.0+/3.0 的入口：

```text
game/Video.cpp:379:15: error: use of undeclared identifier 'glGetStringi'
game/Video.cpp:271:5:  error: use of undeclared identifier 'glDebugMessageCallback'
... use of undeclared identifier 'glGetUniformLocation' / 'glUniform4fv'
```

同一头文件在 Emscripten / Apple 构建下是正常的，这个「只在 OHOS/Linux 挂」的
反差是本模式最典型的入口信号。

## 现象与根因

### 根因①：`GL_GLEXT_PROTOTYPES` 未定义 → 原型整段被裁掉

gl4es 的 `include/GL/gl.h` 只在 Emscripten/Apple 分支里开启原型宏：

```c
/* gl4es include/GL/gl.h */
#if defined(__EMSCRIPTEN__) || defined(__APPLE__)
#  define GL_GLEXT_PROTOTYPES 1
#endif
```

而它的 `include/GL/glext.h` 把 `GL_VERSION_2_0 / 2_1 / 3_0` 的函数声明整段包在
`#ifdef GL_GLEXT_PROTOTYPES` 内。于是 OHOS 上 `<GL/glew.h>`（内部转发到 gl4es 的
`gl.h`）只给出 OpenGL 1.x 原型。

注意：**C 源文件会退化为「隐式声明」告警而放过，C++ 源文件是硬错误**。同一个
工程里 `.c` 能编译、`.cpp` 全挂，极易被误判为「上游源码不兼容 OpenGL 2」而放弃。

### 根因②：GLEW 在 OHOS 制品仓根本不存在

工程普遍写 `find_package(GLEW REQUIRED)`，而 OHOS 制品仓没有 glew 配方或二进制
（需按 R35 用 `conan download`/`conan install` 实测，不能用 `conan list` 下结论）。
但工程真正用到的 GLEW 面很小：

| 面 | 实际内容 |
|---|---|
| 宏 | `GLEW_VERSION`、`GLEW_VERSION_1_1..2_1`、`GLEW_OK` / 错误码、`GLEW_ARB_*` feature flag |
| 函数 | `glewInit()`、`glewGetString(GLEW_VERSION)`（本工程实际只用到这两个） |
| 变量 | `glewExperimental` |

绝大多数 GLEW 宏只是 feature flag，`glewInit` 在「直接用 gl4es 的 libGL」场景里
其实**没有需要初始化的东西**。所以缺口可以用一份极小的下游 shim 一次性补上，
而不必真去适配一个 GLEW 包。

此外 gl4es **不导出**调试入口（`glDebugMessageCallback` / `glDebugMessageControl`）
以及少数 GL 3.x 入口（`glBindBufferBase` / `glProgramParameteri` /
`glBindFragDataLocation`）。这些符号只被工程里**从未被调用**的辅助代码引用
（critter 的 `mooflu.common/utilsgl/gl3/Program.cpp` 即此类），空实现不改变行为。

## 推荐方案

**下游 compat 头 + 极小空实现 shim**（`rec_priority: 1`）：

1. 配方经 `exports_sources` 携带 `compat/GL/glew.h`：在 `#include <GL/gl.h>`
   **之前**定义 `#define GL_GLEXT_PROTOTYPES 1`——gl4es 的 `gl.h` L2097 无条件
   include `glext.h`，而 `glext.h` 的 2.0+/3.0 原型块由 `#ifdef GL_GLEXT_PROTOTYPES`
   门控，宏先就位即让原型随 gl.h 一起可见；再补 GLEW 的宏面与函数面声明。
   （反例：把宏写在 `gl.h` **之后**、再二次 include `glext.h` 是空操作——`glext.h`
   的 `__glext_h_` include guard 会把第二次 include 整段跳过。）
2. `compat/glew-shim.c` 提供空实现：`glewInit()` 返回 `GLEW_OK`、
   `glewGetString()` 返回版本串，加上 gl4es 未导出符号的 no-op（调试入口
   `glDebugMessageCallback`/`glDebugMessageControl` + 3 个 GL 3.x 入口）。
3. CMake 侧把 FindOpenGL 钉在 gl4es 上：
   `-DOPENGL_gl_LIBRARY=<gl4es>/lib/libGL.so`、`-DOPENGL_INCLUDE_DIR=<gl4es>/include`。

参考先例：`archives/l/logstalgia/1.1.4`（同名 `src/GL/glew.h` 头 shim + 静态 shim
库随链接进入产物）、`archives/b/ball`（GLU 不可得时关闭 GUI 面而非硬造依赖）。

## 禁止策略

| 禁止 | 原因 | 后果 |
|---|---|---|
| 装宿主 `libglew-dev` / 从 `/usr/include/GL/glew.h` 取头 | OHOS 目标无系统 GLEW；宿主头会把 `GLEW_VERSION` 报成与 gl4es 实际能力不符的值，运行期走到未实现路径 | 链到宿主非 aarch64-ohos 的 libGLEW，目标机 loader 拒载；致命的是运行期按错误版本号启用 gl4es 未实现路径而崩溃 |
| 把 `GL_GLEXT_PROTOTYPES` 定义放在 gl4es 的 `gl.h` **之后**、再靠二次 include `glext.h` 补救，或直接删源码里的 `#include <GL/glew.h>` | 宏必须在 `gl.h` 被解析**之前**就位（`gl.h` L2097 无条件 include `glext.h`，prototype 块由该宏门控）；放晚了二次 include 会被 `glext.h` 的 `__glext_h_` include guard 整段跳过；改上游源码属越界 | 反复折腾仍报同样的未声明标识符，最后误判为「gl4es 不支持 GL2」而放弃；或留下无法复现的本地改源码 |

## 验证

```bash
# 1) gl4es 头在该平台不定义原型宏（应只出现在 Emscripten/Apple 分支）
grep -n "GL_GLEXT_PROTOTYPES" $GL4ES_PREFIX/include/GL/gl.h
# 2) glext.h 的 2.0+/3.0 声明确实被该宏门控
grep -n "GL_VERSION_2_0\|GL_VERSION_3_0" $GL4ES_PREFIX/include/GL/glext.h | head
# 3) 制品仓确无 glew（R35 口径：用 download 而非 list 下结论）
conan download "glew/2.2.0" -r=ohpcd --only-recipe      # 期望 Recipe not found
# 4) 修好后原型可见且 glew 符号可解析
printf '#include <GL/glew.h>\nint main(){glewInit();return 0;}\n' > t.c \
  && clang t.c -lGL -o t && ./t
```

实测收敛判据（critter 2.0.4）：`cmake --build` 走到
`[84/84] Linking CXX executable game/critter`，产物为
`ELF64 LSB AArch64 / ET_DYN(PIE) / PT_INTERP=/lib/ld-musl-aarch64.so.1`；主机运行
（gl4es GLES 后端）退出码 0，日志含 `LIBGL: Initialising gl4es`、
`LIBGL: Using GLES 2.0 backend`、`INFO: Critter 2.0.4`、`LIBGL: Shutting down`。
