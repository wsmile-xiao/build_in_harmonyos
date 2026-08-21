# libepoxy (epoxy)

Modern libepoxy — GL/EGL function-pointer dispatch library（gtk+ 依赖链）。

- 上游仓库：https://github.com/anholt/libepoxy
- 构建系统：meson
- 平台：OpenHarmony / HarmonyOS PC (aarch64)
- 版权：MIT

## 版本

| 版本 | 状态 | 构建日期 | 说明 |
|------|------|---------|------|
| 1.5.10 | built | 2026-08-20 | OHOS/aarch64 适配，gtk+ 3.24.38 依赖 |

## OHOS 适配说明

epoxy 是 GL/EGL 函数指针派发库，无外部依赖、纯 meson 构建。OHOS/aarch64 适配要点：

1. **无 X11/GLX**：OHOS 无 X11/GLX，meson 需 `-Dx11=false -Dglx=no`，否则生成 glx dispatch 缺 `<GL/glx.h>` 失败。
2. **运行时 dlopen 名称**：OHOS 只有无版本号的 `libEGL.so` / `libGLESv2.so` / `libGLESv3.so`，没有桌面 `libEGL.so.1` / `libGLESv2.so.2` / `libGL.so.1` / `libOpenGL.so.0`。补丁 0001 加 `__OHOS__` 分支映射。
3. **GL/GLES 函数经 eglGetProcAddress 解析**：OHOS `libGLESv2.so` 的 `gl*` 动态符号是 stub（调用返回 NULL），epoxy 的 `gl_dlsym`/`gles1/2/3_dlsym` 在 OHOS 先走 `epoxy_get_proc_address`。
4. **平台宏**：补丁 0002 将 OHOS 归入与 Android 相同的平台分支（EGL 启用、GLX/WGL 禁用）。
5. **codesign**：共享库按 HarmonyOS 要求签名（binary-sign-tool）。

## 使用方法

下游（如 gtk+）通过 Conan 依赖本包：

```python
self.requires("epoxy/1.5.10")
```

提供 `epoxy::epoxy`（CMake）、`epoxy`（pkg-config）。
