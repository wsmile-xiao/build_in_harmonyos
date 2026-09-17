# glu（libGLU）9.0.3

Mesa 的 OpenGL Utility library —— 提供 NURBS、曲面细分（tessellation）、二次曲面
（quadrics）、多级渐远纹理（mipmapping）等桌面 OpenGL 的配套工具函数。

| 项 | 值 |
|----|-----|
| 上游 | https://gitlab.freedesktop.org/mesa/glu |
| 版本 | 9.0.3 |
| 发布归档 | https://archive.mesa3d.org/glu/ |
| 许可 | SGI-B-2.0 |
| 构建系统 | meson |
| 依赖 | `mesa/24.3.4.1`（提供 OSMesa 桌面 GL 实现）|

## OHOS 适配说明

OHOS SDK 只提供 EGL + GLES2/GLES3，**没有桌面 GL**（无 `libGL.so` / `glx.h`）。
而 GLU 是桌面 GL 的配套库——但适配是可行的：

1. **GLU 不需要 GLX**：源码中 `glX` 引用数为 **0**，它只需一份提供 OpenGL API 的实现，
   并不依赖 X11；
2. **Mesa OSMesa 提供该实现**：`mesa/24.3.4.1` 交付 `libOSMesa.so`（离屏软件桌面 GL）
   与 `include/GL/gl.h`，无需 X11/Wayland/DRM；
3. **glu 原生支持**：meson 的 `gl_provider` 选项 choices 即
   `['glvnd', 'gl', 'osmesa']`，用 `-Dgl_provider=osmesa` 即可。

### 关键改动：恢复符号导出（补丁 0001）

上游 `src/meson.build` 无条件设置 `gnu_symbol_visibility: 'hidden'`，而源码中没有任何
`visibility default` 标注 —— 结果**编译成功、产物大小正常，但动态符号表导出 0 个
`glu*` 符号**（均为 `LOCAL HIDDEN`），消费者无法链接。本包删除该行，
使 64 个 `glu*` 符号正常导出（`gluOrtho2D` 等为 `GLOBAL DEFAULT`）。

### `.pc` 名称对齐

mesa 的 `package_info` 未设 `pkg_config_name`，`PkgConfigDeps` 只生成 `mesa.pc`，
而 glu 查找的是 `dependency('osmesa')`。本包在 `generate()` 中复制 mesa 包内的
`osmesa.pc` 并修正其 `prefix`（包内写死为 `/`），否则 pkg-config 会发出
`-L/lib` 导致 `unable to find library -lOSMesa`。

## 构建

```bash
conan create archives/g/glu/9.0.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 测试

`test_package/` 真实编译并**执行**消费者程序，验证链接与符号可用：
调用 `gluErrorString()`（纯函数，无需 GL 上下文）并校验返回值。
详见 `test_package/MANIFEST.yml`。

> 说明：GLU 的完整功能（NURBS / tessellation / quadrics）需要 GL 上下文与渲染
> target，OHOS 上的验证需要显示服务；test_package 因此选用不依赖上下文的 API
> 做确定性断言，并额外校验 `glu*` 符号确实被导出（这正是补丁 0001 的修复点）。
