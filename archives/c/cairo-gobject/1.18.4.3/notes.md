# cairo-gobject 1.18.4.3 适配笔记（xlib surface 版）

## 背景
gtk 3.24.52 启用 X11 后端需要 cairo 的 xlib surface 支持。制品仓 `cairo-gobject/1.18.4.2`
打包的 libcairo.so 为 xlib=disabled 版（无 cairo_xlib_* 符号），gtk 链接 X11 后端时
同名 SONAME 去重会命中无 xlib 的 libcairo → 链接失败。按 R37 发布 **1.18.4.3**（xlib 版）。

## 相对 1.18.4.2 的变更
- `generate()`：`xlib=enabled`（glib 保持 enabled）
- `requirements()` 增加：libx11/6.4.0（override，压 libxrender 的 libx11/1.8.13 传递 pin）、
  libxext/6.4.0、libxrender/0.9.12
- `build_requirements()`：tool_requires meson/1.11.0（CI 无全局 meson）
- `package_info()`：cpp_info.requires 补 libxext/libxrender（libx11 为 override 非直接依赖，不列入）

## 构建验证
```bash
conan create archives/c/cairo-gobject/1.18.4.3 --version=1.18.4.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
- 打包的 libcairo.so 带 cairo_xlib_surface_create 等符号（strings 核验 11 处）
- test_package：cmake 构建 + 真实 API 调用（1/1）

## 注意事项
- 版本后缀 1.18.4.3 与制品仓 1.18.4/1.18.4.2 共存；下游 gtk 引用本包
- 构建环境需 python 自身 lib 前置（glib 包 libintl 遮蔽问题，见 gtk 配方 libintl 处理）

**编译日期**: 2026-09-08
**状态**: built（本地 W3 验证通过）
