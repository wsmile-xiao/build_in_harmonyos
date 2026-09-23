# cairo 1.18.4.1 适配笔记（xlib surface 版）

## 背景
gtk 3.24.52 启用 X11 后端需要 cairo 的 xlib surface 支持（`cairo-xlib.h` / `cairo_xlib_surface_*`
符号）。制品仓 `cairo/1.18.4` 为 OHOS 适配时硬编码 `xlib=disabled`（鸿蒙无 X11），无 xlib 能力。
按 R37 版本号策略发布 **cairo/1.18.4.1**（同上游版本适配修复后缀），启用 xlib + glib。

## 相对 1.18.4 的变更
- `generate()`：`xlib=enabled`、`glib=enabled`（其余选项与 1.18.4 一致：xcb/xlib-xcb/quartz/dwrite/lzo/spectre 关闭，tests=auto）
- `requirements()` 增加：libx11/6.4.0（override，压 libxrender 的 libx11/1.8.13 传递 pin）、
  libxext/6.4.0、libxrender/0.9.12、glib/2.84.0.1（gobject 绑定）
- `build_requirements()`：tool_requires meson/1.11.0（CI 无全局 meson）
- 补丁沿用 1.18.4（0001/0002 tmpfile 修复），conandata patches 键改为 1.18.4.1

## 构建验证
```bash
conan create archives/c/cairo/1.18.4.1 --version=1.18.4.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
- xlib surface 源码编译进 libcairo.so（cairo-xlib-surface.c 等），cairo-xlib.pc 随包安装
- test_package：头闭包编译 + dlopen libcairo.so 运行期可加载（1/1）

## 注意事项
- 版本后缀 1.18.4.1 与制品仓 1.18.4 共存，下游 gtk 精确引用 1.18.4.1；其余下游不受影响
- glib 启用后 cairo 包自带 `CAIRO_HAS_GOBJECT_FUNCTIONS` 宏，gtk 配方的 cairo 头覆盖逻辑可跳过
- libx11 为 override 钉版（6.4.0），cairo 的 cpp_info 不声明 libx11 引用（override 非直接依赖）

**编译日期**: 2026-09-08
**状态**: built（本地 W3 验证通过）
