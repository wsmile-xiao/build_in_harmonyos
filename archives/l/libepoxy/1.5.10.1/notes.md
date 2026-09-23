# libepoxy 1.5.10.1 适配笔记（GLX 版）

## 背景
gtk 3.24.52 启用 X11 后端时 `gdk/x11/gdkglcontext-x11.h` 需要 `<epoxy/glx.h>`。
制品仓 `libepoxy/1.5.10` 在 OHOS 下硬编码 `glx=no`、`x11=false`（鸿蒙无窗口系统），
不生成 epoxy/glx.h。按 R37 发布 **1.5.10.1**（GLX 版）。

## 相对 1.5.10 的变更
- `generate()`：OHOS 分支改为 `glx=yes`、`x11=true`（egl 保持 no——X11 后端用 GLX）
- `requirements()` 增加：xorgproto/2025.1（GL/glx.h）、libx11/6.4.0（X11/Xlib.h，epoxy/glx.h 内 include）
- 补丁沿用 1.5.10（0001-python3-gen-dispatch.patch）

## 构建验证
```bash
conan create archives/l/libepoxy/1.5.10.1 --version=1.5.10.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
- 包内 include/epoxy/glx.h 生成；libepoxy 编译链接通过（R26 静态，default_options shared=False）

## 注意事项
- 版本后缀 1.5.10.1 与制品仓 1.5.10 共存；下游 gtk 精确引用 1.5.10.1
- 其余 OHOS 下游不受影响（仍用 1.5.10）

**编译日期**: 2026-09-08
**状态**: built（本地 W3 验证通过）
