# DRAFT-sdl2-2.30.10-egl-querydevices-fallback: OHOS libEGL 无 eglQueryDevicesEXT 时，SDL_EGL 回退 eglGetDisplay(EGL_DEFAULT_DISPLAY) 建立 display

> **Contributor**: Rourou2285 | **Status**: Draft（pending editor review）| **Updated**: 2026-09-01
> **Source**: sdl2 2.30.10.1 HarmonyOS PC 适配（build_in_harmonyos，archives/s/sdl2/2.30.10.1）
> **拟提升编号：由知识库主编确认** —— 本草稿为未提升草稿，尚未分配正式 E 编号

## 场景

在 OpenHarmony (OHOS) PC 上使用 SDL2 创建 OpenGL 上下文时，`SDL_GL_CreateContext` 直接失败，应用报不出 display，无法进入 GL 渲染流程。

## 问题

可复用问题签名（日志症状）：

```text
Could not initialize EGL|Could not create OpenGL context|SDL_GL_CreateContext failed
# 或 glGetError 报错 / eglQueryDevicesEXT 相关 log
```

真实证据（sdl2 2.30.10.1，OHOS PC aarch64，GPU=HUAWEI Maleoon 916）：
- SDL 默认 EGL 路径 `SDL_EGL_ChooseAndInitDisplay` **硬性要求 `eglQueryDevicesEXT`**（来自 `EGL_EXT_device_enumeration`）；
- OHOS 的 `libEGL.so` **不导出 `eglQueryDevicesEXT`** → SDL 无法从设备枚举中选到 display → `SDL_GL_CreateContext` 失败；
- 结果：任何在 OHOS 上用 SDL2 建 GL 上下文的应用（含 AC 这类通过 SDL 管理 GL 上下文的游戏）都卡在这里。

## 根因

SDL 的 `SDL_EGL_ChooseAndInitDisplay` 把 `eglQueryDevicesEXT` 当作**必需**能力：缺失即提前返回错误，而不尝试回退到老的 `eglGetDisplay(EGL_DEFAULT_DISPLAY)`。OHOS 提供的基础 EGL 只保证经典 `eglGetDisplay`，不保证设备枚举扩展，因此二者必须兼容共存。

## 修复（最小方案）

修改 `src/video/SDL_egl.c` 的 `SDL_EGL_ChooseAndInitDisplay`：检测到 `eglQueryDevicesEXT` 不可用时，回退 `eglGetDisplay(EGL_DEFAULT_DISPLAY)` 建立 display。

```c
/* 在 eglQueryDevicesEXT 探测失败/缺失时 */
_this->egl_data->egl_display =
    _this->egl_data->eglGetDisplay(EGL_DEFAULT_DISPLAY);
```

关键：`eglGetDisplay(EGL_DEFAULT_DISPLAY)` 是经典 EGL 1.0 入口，OHOS libEGL 一定实现；回退路径不依赖 `EGL_EXT_device_enumeration`。

## 验证

- 补丁 `0006-src-video-SDL_egl.c.patch` 应用后，SDL 头 `SDL_GL_CreateContext` 成功；
- OHOS 真机 GLES3.2（Maleoon 916）`SDL_GL_CreateContext` 返回非空，`glReadPixels` 出图非黑；
- `conan-verify sdl2 2.30.10.1` 全过（G0-G4、L2/L4/L5）；上游 testautomation 306 用例随 `build()` 集成运行并通过，`test_SDL2` 消费冒烟经 ctest 通过。

## 可复用边界

- 适用：任何在 OHOS 上用 SDL2 创建 GL/GLES 上下文的应用（`SDL_GL_CreateContext` / 窗口 EGL 路径）；
- 限制：需要真实 EGL 环境才能验证回退是否触发（纯离线/无 EGL 环境仅能验证编译链接）；
- 查重：对 `eglQueryDevicesEXT`/`eglGetDisplay`/`SDL_EGL_ChooseAndInitDisplay`/`SDL_GL_CreateContext`/`OHOS EGL` 在 `knowledge/` 及索引全量检索**无等价条目**（`E321-B1GL` 为 gl4es 桌面 GL→GLES2 兼容层、`astromenace-1.3.2-gles2-null-context` 为无上下文时 GLES2 判空防护，均非本问题）。

## 关联条目

- `E321-B1GL`：OHOS 无桌面 OpenGL(libGL) 用 gl4es 补兼容层 —— 解决"固定管线函数用不了"；本稿解决"SDL 连 GL 上下文都建不出来"，二者组成闭环（上下文层 + 兼容层）。
- `astromenace-1.3.2-gles2-null-context`：无 GL 上下文时调用真实 GLES2 的 SIGSEGV 判空防护 —— 运行时符号/上下文判空，与本稿的 display 初始化回退不同层面。
