# freeglut 3.6.0（鸿蒙 PC 适配）

freeglut 是 GLUT（OpenGL Utility Toolkit）的开源实现 —— 提供窗口/上下文管理、
事件循环与回调框架，是大量经典 OpenGL 示例与教学程序的入口库。

| 项 | 值 |
|----|-----|
| 上游 | https://github.com/freeglut/freeglut |
| 版本 | 3.6.0 |
| 许可 | X11（MIT-like）|
| 构建系统 | CMake |
| 适配平台 | OpenHarmony / HarmonyOS PC (aarch64) |
| 渲染后端 | EGL 1.4 (OpenHarmony) + OpenGL ES（pbuffer 离屏表面）|

## 为什么需要移植（而不是改几个参数）

3.6.0 确实自带 EGL/GLES 后端（`src/egl/`），但 **EGL 后端只管理渲染上下文，
  不提供窗口系统**。freeglut 的平台层契约是 **46 个 `fgPlatform*` 函数**，而
  `src/egl/` 只实现了 3 个（`fgPlatformSetWindow` / `fgPlatformDestroyContext` /
  `fgPlatformGlutSwapBuffers`）；其余全部由上游各平台后端实现，且每个后端都绑定
  一个 OHOS 上不存在的窗口系统：

| 上游后端 | 依赖 | OHOS |
|----------|------|------|
| X11 | `X11/Xlib.h`、`libX11` | ❌ 无 |
| Wayland | `wayland-client` | ❌ 无 |
| Android | `android_native_app_glue` | ❌ 无 |
| BlackBerry | `bps` / `screen` / `slog2` | ❌ 无 |
| mswin / OGC | Win32 / GameCube | ❌ 不适用 |

因此本适配**新写了 OHOS 平台后端**（`src/ohos/`，3 个文件）：

| 文件 | 作用 |
|------|------|
| `fg_internal_ohos.h` | 平台内部类型（`SFG_PlatformDisplay` / `SFG_PlatformContext` / joystick / window-state）|
| `fg_ohos.c` | 平台层实现：display 生命周期、窗口（pbuffer）、主循环、状态查询、光标、gamemode、spaceball、joystick、dial |
| `fg_gl_dispatch_ohos.c` | GL 入口调度层 + GLES1 兼容桩 + 串口 API 桩 |

## 设计：EGL pbuffer 离屏渲染

OHOS 没有窗口系统，但**普通原生进程即可用 EGL**。实测探针结果：

```
eglGetDisplay(EGL_DEFAULT_DISPLAY) -> 有效
EGL 1.4   vendor=OpenHarmony   client apis=OpenGL_ES   configs=25
extensions 含 EGL_KHR_surfaceless_context
eglChooseConfig(EGL_PBUFFER_BIT) → eglCreatePbufferSurface → eglCreateContext(GLES2) 均成功
GL_VERSION=OpenGL ES 3.2 B301    GL_RENDERER=Maleoon 916
```

于是平台层基于 **EGL pbuffer 表面**实现。语义取舍：`glutCreateWindow()`
创建的是「请求尺寸的离屏渲染目标」；窗口位置/标题/图标化/光标/gamemode 等请求
被接受并记录，但无视觉效果（无合成器响应）。

## 关键坑一：GL 直连符号是调度空桩

`libGLESv2.so` 导出的 GL 符号在 OHOS 上是**调度桩**，不是驱动真函数。
实测对照（同一进程、同一个已 MakeCurrent 的 GLES2 上下文）：

| 取函数方式 | `glGetString(GL_VERSION)` | 绘制效果 |
|-----------|--------------------------|---------|
| 直连链接符号 | **NULL** | 无报错但不生效 |
| `eglGetProcAddress()` | `"OpenGL ES 3.2 B301"` | 真渲染 |

freeglut 内部直接调用 GL 函数，不加处理则所有调用静默命中空桩。
`fg_gl_dispatch_ohos.c` 把受影响的入口包一层经 `eglGetProcAddress()` 解析，
并以 `-Wl,-Bsymbolic` 链接，使**库内**调用绑定到本库包装函数。
效果：库内残留未定义 GL 符号 **13 → 0**。

## 关键坑二：OHOS 无 GLES1

OHOS 只有 GLES2/GLES3，`GLES/gl.h` 与 `libGLESv1_CM` 均不存在，而上游核心仍
引用 GLES1 固定管线入口（`glBegin`/`glEnd`/`glVertex3fv`/`glNormal3fv`/
`glTexCoord2fv`/`glColor4fv` 等）。实测经 `eglGetProcAddress` 探测，
这 7 个中仅 `glColor4f` 可解析，其余均为 NULL。故在调度层内提供 no-op 桩并告警。

**后果（如实声明）**：依赖 GLES1 固定管线的内部绘制路径在 OHOS 上**不渲染** ——
包括位图字体（`glutBitmapCharacter`）、菜单渲染、quadrics/NURBS 立即模式输出。
其余功能（窗口/上下文生命周期、状态查询、`glutSwapBuffers`、应用侧用 GLES2
shader 自行渲染）均正常。

## 构建

```bash
conan create archives/f/freeglut/3.6.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 测试

`test_package/` 在真机（HarmonyOS aarch64）**真实执行**：注册 display 回调、
触发重绘、用 GLES2 shader 画三角形并 `glReadPixels` 校验中心像素为蓝色。
详见 `test_package/MANIFEST.yml`。

实测输出：

```
[display #1] GL_VERSION=OpenGL ES 3.2 B301 RENDERER=Maleoon 916 missing=0
[display #1] shader v=1 f=1 link=1
[display #1] center pixel=0,0,255,255 <- triangle rendered
SUMMARY display_calls=2 shader=OK render=OK missing_procs=0
RESULT=ALL_OK
```

## 已知限制

1. **无窗口系统** —— pbuffer 离屏渲染，无可见窗口；位置/标题等仅有记录语义。
2. **无输入事件** —— OHOS 原生进程不接收输入事件，`fgPlatformProcessSingleEvent()`
   为空实现；输入需宿主应用（ArkTS/XComponent）转发，上游 API 未覆盖该场景。
3. **GLES1 固定管线路径不可用** —— 见上（位图字体/菜单/quadrics 不渲染）。
4. **gamemode / spaceball / joystick 无能力** —— 接口存在但为空实现。
