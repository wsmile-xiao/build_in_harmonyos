# freeglut 3.6.0 适配笔记

## 编译环境
- 构建系统: cmake（+ ninja/make）
- 编译日期: 2026-09-15
- 编译器: clang 15（aarch64-linux-ohos）
- 状态: built

## 上游

| 项 | 值 |
|----|-----|
| 仓库 | https://github.com/freeglut/freeglut |
| 版本 | 3.6.0（tag `v3.6.0`）|
| 发布归档 | `https://github.com/freeglut/freeglut/releases/download/v3.6.0/freeglut-3.6.0.tar.gz` |
| sha256 | `9c3d4d6516fbfa0280edc93c77698fb7303e443c1aaaf37d269e3288a6c3ea52` |
| 大小 | 429,619 字节 |
| 许可 | X11（MIT-like）|

## 核心难点

freeglut 理论上「可适配」——3.6.0 带 EGL/GLES 后端（`src/egl/`，11 个文件）——
但**EGL 后端只提供渲染上下文管理，不提供窗口系统**。freeglut 的平台层契约是
**46 个 `fgPlatform*` 函数**，其中 `src/egl/` 只定义了 3 个
（`fgPlatformSetWindow` / `fgPlatformDestroyContext` / `fgPlatformGlutSwapBuffers`）。
上游其余后端（X11 / Wayland / Android / BlackBerry / mswin / OGC）都各自实现
几十个函数，且每个都绑定一个 OHOS 上不存在的窗口系统：

| 后端 | 依赖 | OHOS |
|------|------|------|
| x11 | `X11/Xlib.h` | ❌ 无 |
| wayland | `wayland-client` | ❌ 无 |
| android | `android_native_app_glue` | ❌ 无 |
| blackberry | `bps/screen/slog2` | ❌ 无 |
| mswin / ogc | Win32 / GameCube | ❌ 不适用 |

故 OHOS **必须新写一个平台后端**，而不是「打补丁 + 复用现有后端」。
实测证据（默认走 X11 分支时）：

```
src/x11/fg_internal_x11.h:38:10: fatal error: 'X11/Xlib.h' file not found
```

## 解决路径：EGL pbuffer 离屏渲染

关键发现：**OHOS 的 EGL 在普通原生进程里即可用，无需窗口系统**。实测探针：

```
eglGetDisplay(EGL_DEFAULT_DISPLAY) -> 有效
EGL 1.4  vendor=OpenHarmony   client apis=OpenGL_ES   configs=25
extensions 含 EGL_KHR_surfaceless_context
eglChooseConfig(EGL_PBUFFER_BIT) 成功 → eglCreatePbufferSurface 成功
eglCreateContext(GLES2) 成功 → eglMakeCurrent 成功
GL_VERSION=OpenGL ES 3.2 B301   GL_RENDERER=Maleoon 916
glClearColor + glClear + glReadPixels -> pixel=255,0,0,255（真渲染）
```

于是平台层基于 **EGL pbuffer 表面**实现（无窗口/离屏渲染）。
语义上的取舍：OHOS 无窗口管理器，`glutCreateWindow()` 实际创建的是
「请求尺寸的离屏渲染目标」，窗口位置/标题/图标化/光标/gamemode/spaceball
等请求被接受并记录但无视觉效果（无合成器响应）。

## 第二难点：GL 直连符号是调度空桩

`libGLESv2.so` 导出的 GL 符号在 OHOS 上是**调度桩**，不是驱动真函数。实测对照
（同一进程、同一个已 MakeCurrent 的 GLES2 上下文）：

| 取函数方式 | 结果 |
|-----------|------|
| 直连 `glGetString(GL_VERSION)` | **NULL** |
| `eglGetProcAddress("glGetString")` | `"OpenGL ES 3.2 B301"` |
| 直连 `glClear`+`glReadPixels` | 无报错但**画面未改变** |
| `eglGetProcAddress` 取到的同名入口 | 真渲染 |

freeglut 内部直接调用 GL 函数，若不加处理，其所有 GL 调用都会静默命中空桩。
故新增 `src/ohos/fg_gl_dispatch_ohos.c`：

1. 把受影响的 GL 入口包一层，经 `eglGetProcAddress()` 解析真函数；
2. 用 `-Wl,-Bsymbolic` 链接，使**库内**调用绑定到本库的包装函数，
   而不是解析到 `libGLESv2.so` 的空桩。

实测修复效果：库内残留未定义 GL 符号从 **13 个降到 0 个**；
消费者可正常链接并在运行期真渲染。

## 第三难点：OHOS 无 GLES1

OHOS 只有 GLES2/GLES3（`GLES2/gl2.h`、`libGLESv2.so`），
**没有 GLES1**：`GLES/gl.h` 与 `libGLESv1_CM` 均不存在。而上游 freeglut 核心
仍引用 GLES1 固定管线入口（`fg_font.c`、`fg_menu.c`、`fg_geometry.c`）：

```
glBegin glEnd glColor4f glColor4fv glNormal3fv glTexCoord2fv glVertex3fv
```

实测用 `eglGetProcAddress` 探测：仅 `glColor4f` 可解析，其余 6 个返回 NULL
（即 OHOS 上确实无实现）。故在调度层内提供 no-op 桩并**一次性告警**。

**后果（如实声明）**：freeglut 内部依赖 GLES1 固定管线的绘制路径在 OHOS 上
**不渲染** —— 包括位图字体（`glutBitmapCharacter`）、菜单渲染、以及
quadrics/NURBS 的立即模式输出。其余功能（窗口/上下文生命周期、状态查询、
缓冲区交换、以及应用侧自行用 GLES2 shader 渲染）均正常。

## 其余适配点

| # | 问题 | 根因 | 解决 |
|---|------|------|------|
| 1 | `FindOpenGL` 找不到 EGL/GLES2 | CMake 的 FindOpenGL 不会搜索交叉 sysroot | 配方显式传 `OPENGL_egl_LIBRARY` / `OPENGL_gles2_LIBRARY` / `OPENGL_*_INCLUDE_DIR` |
| 2 | `Could not find GLES1_LIBRARY` | 上游 `FIND_LIBRARY(... REQUIRED)` 强制 GLESv1_CM | 补丁对 HarmonyOS 置空该变量并豁免 |
| 3 | `OpenGL::OpenGL` 目标不存在 | GLES 分支的 LIBS 引用了桌面 GL 组件 | 补丁在 HarmonyOS 下从 LIBS 移除 |
| 4 | `cmake_minimum_required(VERSION 3.1.2)` | CMake 4.x 移除了 <3.5 兼容 | 传 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 5 | `glutCreateWindow` 报 "called without first calling glutInit" | 各平台 init 都需置 `fgState.Initialised = GL_TRUE`，OHOS 后端漏了 | 我的 `fgPlatformInitialize` 中补上（并 `atexit(fgDeinitialize)`）|
| 6 | 链接期 `undefined reference to fg_serial_*` | 串口拨号设备 API 需平台提供 | 调度层内提供桩（返回 NULL/EOF）|

## 验证结果

`conan create` 端到端通过（本机即 HarmonyOS aarch64 设备，真实执行）：

```
  1) glutInit OK
  2) glutCreateWindow -> 1  (300x300)
  3) 重绘 #1
  [display #1] GL_VERSION=OpenGL ES 3.2 B301 RENDERER=Maleoon 916 missing=0
  [display #1] shader v=1 f=1 link=1
  [display #1] center pixel=0,0,255,255 <- triangle rendered
  4) 重绘 #2
  [display #2] GL_VERSION=OpenGL ES 3.2 B301 RENDERER=Maleoon 916 missing=0
  [display #2] shader v=1 f=1 link=1
  [display #2] center pixel=0,0,255,255 <- triangle rendered
  5) glutDestroyWindow OK

SUMMARY display_calls=2 shader=OK render=OK missing_procs=0
RESULT=ALL_OK
```

test_package 覆盖：`glutInit` → `glutCreateWindow` → 注册 display 回调 →
`glutPostRedisplay`+`glutMainLoopEvent` 触发渲染 → 应用侧编译链接 GLES2
shader、绘制三角形并 `glReadPixels` 校验像素 → `glutSwapBuffers` →
`glutDestroyWindow`。断言为**具体数值**（中心像素蓝通道 > 200），非恒真。

## 依赖版本
- OHOS SDK 自带 `libEGL.so` / `libGLESv2.so`（sysroot 内）
- 制品仓 `egl/1.0.5`、`gles2/2.0.25`（同族 cogl 亦使用）

## 已知限制

1. **无窗口系统**：pbuffer 离屏渲染，无可见窗口；位置/标题等为记录语义。
2. **无输入事件**：OHOS 原生进程不接收输入，`fgPlatformProcessSingleEvent()`
   为空；输入需由宿主应用（ArkTS/XComponent）转发，上游 API 未覆盖此场景。
3. **GLES1 固定管线路径不可用**：位图字体/菜单/quadrics 立即模式不渲染（见上）。
4. **无 gamemode / spaceball / joystick**：平台无对应能力，接口存在但为空实现。

---

**最终状态**: built
