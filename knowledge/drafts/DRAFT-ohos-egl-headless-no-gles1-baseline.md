# DRAFT-ohos-egl-headless-no-gles1-baseline — OHOS 无窗口系统，但 EGL 离屏可用：窗口工具库的移植基线

> **对应结构化数据**：`knowledge/drafts/DRAFT-ohos-egl-headless-no-gles1-baseline.kv`
> **验证实例**：freeglut 3.6.0（PR #10168，OHOS PC aarch64，SDK 26，GPU = HUAWEI Maleoon 916）
> **Status**: DRAFT ｜ **Severity**: 🟡 medium ｜ **Updated**: 2026-09-15

## 1. 一句话

OHOS 没有 X11 / Wayland / Android-glue，**但普通原生进程即可用 EGL 离屏渲染**
（`EGL_DEFAULT_DISPLAY` + `EGL_KHR_surfaceless_context` + pbuffer）——
因此「窗口系统 + GL 上下文」型的工具库**可以适配**，方法是**新写一个 OHOS 平台后端**，
而不是复用上游任何后端、也不是判定不可适配。同时 **OHOS 无 GLES1**，固定管线入口须自备桩。

## 2. 两个常见误判（都不对）

### 误判 A：「没有窗口系统 → 不可适配」

错。**「无窗口系统」≠「不能渲染」。** OHOS 的 EGL 在普通原生进程里就能用，无需合成器。

### 误判 B：「库自带 EGL 后端 → 打补丁就能用」

错，且低估一个数量级。**EGL 后端 ≠ 窗口系统。** 以 freeglut 为例：

| 项 | 数量 |
|----|------|
| 平台层契约（核心引用的 `fgPlatform*`）| **46 个** |
| `src/egl/` 实现的 | **3 个**（`fgPlatformSetWindow` / `fgPlatformDestroyContext` / `fgPlatformGlutSwapBuffers`）|
| 需新写 | **约 43 个** |

`src/egl/` 只负责「渲染上下文管理」，不负责窗口、事件循环、光标、状态查询。
其余全由各平台后端（x11 / wayland / android / blackberry / mswin / ogc）实现，
而**每个后端都绑定一个 OHOS 上不存在的窗口系统**：

| 上游后端 | 依赖 | OHOS |
|----------|------|------|
| X11 | `X11/Xlib.h`、`libX11` | ❌ |
| Wayland | `wayland-client` | ❌ |
| Android | `android_native_app_glue` | ❌ |
| BlackBerry | `bps` / `screen` / `slog2` | ❌ |
| mswin / OGC | Win32 / GameCube | ❌ 不适用 |

实测（默认落入 X11 分支）：

```
src/x11/fg_internal_x11.h:38:10: fatal error: 'X11/Xlib.h' file not found
```

## 3. 可行性证据：EGL 探针（约 66 行，不依赖任何三方库）

```c
eglGetDisplay(EGL_DEFAULT_DISPLAY)   -> 有效
EGL 1.4  vendor=OpenHarmony  client apis=OpenGL_ES  configs=25
extensions 含 EGL_KHR_surfaceless_context
eglChooseConfig(EGL_PBUFFER_BIT) -> eglCreatePbufferSurface -> eglCreateContext(GLES2)  全部成功
eglMakeCurrent 成功
GL_VERSION  = "OpenGL ES 3.2 B301"
GL_RENDERER = "Maleoon 916"
glClearColor(1,0,0,1)+glClear+glReadPixels -> pixel = 255,0,0,255   ← 真渲染
```

> ⚠️ 探针里读 `GL_VERSION` 必须经 `eglGetProcAddress` 取函数，否则得到 `NULL`
> —— 详见 `DRAFT-ohos-gl-symbols-are-dispatcher-stubs`。

## 4. 推荐方案：新写独立 OHOS 平台后端（EGL pbuffer）

**核心原则：新增独立平台目录（如 `src/ohos/`），上游文件零改动。**
不要去改造上游的 x11/wayland 后端 —— 成本更高且必然与上游升级冲突。

实施步骤：

1. **先用探针验证 EGL 离屏可用**（可行性的前提，必须先验）；
2. **用工具清点工作量**，别凭印象估算：
   ```bash
   grep -rhoE '\bfgPlatform[A-Za-z_0-9]+\b' src/*.c | sort -u | wc -l      # 契约总数
   grep -rhoE '\bfgPlatform[A-Za-z_0-9]+\b' src/egl/*.c | sort -u | wc -l  # EGL 层已提供
   ```
3. 实现平台内部头（`SFG_PlatformDisplay` / `SFG_PlatformContext` 等），
   参照 android / blackberry 的内部头结构，但**去掉所有原生窗口依赖**；
4. 构建系统按平台名选择源码目录（CMake 用
   `CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"` —— OHOS 的 Conan CMakeToolchain
   会把 OHOS 映射为 `HarmonyOS`）；**平台标识由构建系统注入抽象宏**，不在 patches/
   里裸用 `__OHOS__`（R8）：
   ```cmake
   # CMakeLists.txt：注入抽象宏
   ADD_DEFINITIONS(-DTARGET_HOST_OHOS)
   ```
   ```c
   /* 库内部头（已含 fg_internal.h 等）用抽象宏 */
   #if TARGET_HOST_OHOS
   ...
   #endif
   /* 装给消费者的公共头：用 __has_include 按头文件是否存在判定，不引入平台宏 */
   #if defined(__has_include) && __has_include(<GLES/gl.h>)
   ...
   #endif
   ```
   > ⚠️ R8：`#ifdef __OHOS__` 在源码/patches/ 中**默认禁止**（应通过构建系统注入
   > 抽象宏或 feature-detection 解决）；本 PR 曾因草稿此处教唆 `__OHOS__` 被 review
   > 指出，已按上方方案改正。
5. **语义取舍如实声明**（见下节）。

### 同步处理的移植摩擦（同批出现，与窗口系统无关）

| # | 现象 | 解决 |
|---|------|------|
| 1 | `Could NOT find OpenGL (missing: OPENGL_egl_LIBRARY ...)` | CMake 的 `FindOpenGL` 只搜宿主不搜交叉 sysroot → 配方显式传 `OPENGL_egl_LIBRARY` / `OPENGL_gles2_LIBRARY` / `OPENGL_*_INCLUDE_DIR` |
| 2 | `Could not find GLES1_LIBRARY using the following names: GLESv1_CM` | 上游 `FIND_LIBRARY(... REQUIRED)` 强制 GLESv1 → 对 HarmonyOS 置空并豁免 |
| 3 | GLES 分支引用桌面 GL 组件（`OpenGL::OpenGL`）| 对 HarmonyOS 从 `LIBS` 移除 |
| 4 | `fatal error: 'GLES/gl.h' file not found` | OHOS 无 GLES1 头 → 条件化该 include + 补齐核心仍引用的 GLES1 常量 |
| 5 | `Unknown linker(s): [['llvm-ar-15'], ...]` | 交叉工具链 binutils 不在 PATH → 从编译器同目录推导 `ar`/`ranlib` 写入 meson native file |
| 6 | `glutCreateWindow` 报 "called without first calling glutInit" | **平台 init 必须置 `fgState.Initialised = GL_TRUE`**（各上游后端均如此，新后端易漏）|

## 5. 必须如实声明的语义取舍

新后端在 OHOS 上**没有窗口系统**，因此：

| 能力 | 实际语义 |
|------|---------|
| `glutCreateWindow()` | 创建「请求尺寸的**离屏渲染目标**」，不是可见窗口 |
| 位置 / 标题 / 图标化 / 光标 / gamemode | 请求被**接受并记录**，但**无视觉效果**（无合成器响应）|
| 输入事件 | **无事件源** —— 事件循环为空；输入需宿主应用（ArkTS/XComponent）转发，上游 API 未覆盖 |
| GLES1 固定管线绘制路径 | **不渲染**（OHOS 无 GLES1）—— 如位图字体、菜单、quadrics/NURBS 立即模式 |

**这些不是缺陷，是平台能力边界**，必须在 README / notes / PR 描述与 test_package 里写清。

## 6. 禁止

- ❌ **「没有窗口系统所以不可适配」** —— 无窗口 ≠ 不能渲染；正确结论是「需新写平台后端」。
- ❌ **「有 EGL 后端就能直接用」** —— EGL 只管理上下文，契约函数还差约 43 个。
- ❌ **用 GLES2 替代 GLES1 固定管线** —— GLES2 里没有 `glBegin`/`glEnd`/`glVertex3fv`，
  二者是「有/无」关系。
- ❌ **改造上游 x11/wayland 后端** —— 成本高且与上游升级必然冲突；应新增独立平台目录。
- ❌ **用空实现换取编译通过就报「适配完成」** —— 空桩只是过渡手段，必须如实声明不可用的
  功能面（E471 同款原则：不得把显示依赖测试写成通过、不得强行 headless 假装通过）。

## 7. 与既有条目的关系（差异化定位）

| 既有条目 | 关系 |
|---------|------|
| **E471**（OHOS PC 无任何原生显示后端，gtkmm）| 那条讲**无显示服务**导致 `gtk_init` 失败与测试分类原则；本条讲**「无窗口系统但 EGL 离屏可用」** 这一正面结论，以及据此移植整套平台层的方法 |
| **E321**（gl4es 补桌面 GL 固定管线，B1 方案）| 那条解决「缺**桌面 GL / 固定管线**」（补一个 `libGL.so` 兼容层）；本条解决「缺**窗口系统**」（新写平台后端，用 GLES2 原生上下文）。两者是互补的两条轴：E321 补 API 面，本条补窗口面；E321 也提到 OHOS 有 EGL 窗口表面，但未给出「普通进程可用 `EGL_DEFAULT_DISPLAY` + surfaceless + pbuffer 实现整套窗口工具库」的结论 |
| **E527**（无 X11 相关）| 同族背景条目 |
| **DRAFT-ohos-gl-symbols-are-dispatcher-stubs** | 本条的配套条目：那条讲符号获取路径（直连为空桩，须 `eglGetProcAddress`），本条讲平台层怎么搭 |

> 查重（2026-09-15）：main 上 `surfaceless` / `无窗口系统` / `no window system` / `GLES1` /
> `GLESv1` 均 **0 命中**；`pbuffer` 命中 E321，但那是在讲 **gl4es** 时把 pbuffer 当**验证手段**
> （`离屏验证：EGL pbuffer GLES2 上下文 + gl4es`），**不是移植策略**；`离屏` 另命中
> DRAFT-mesa（进程名断言 + softpipe 离屏渲染），亦非本条主题。本条为空白领域。

## 8. 方法论提炼

1. **可行性先验证，再估工** —— 一个 66 行的 EGL 探针就能决定「能不能做」，别先读几千行代码。
2. **工作量用工具清点** —— `grep` 契约函数数减去 EGL 层已实现数，比凭印象估靠谱。
3. **新写独立后端，不动上游** —— 保持上游文件零改动，merge 冲突面最小。
4. **平台能力边界必须如实声明** —— 无窗口/无输入/无 GLES1 是客观边界，写清楚；
   绝不用空实现冒充「适配完成」。
