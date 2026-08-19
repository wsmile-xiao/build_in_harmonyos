# librsvg 2.62.3 编译笔记

## 编译概述

**软件**: librsvg
**版本**: 2.62.3
**状态**: built（round-9 CI PASS，上游测试真实运行）
**日期**: 2026-08-14（构建）

## 背景

2.62.2 旧 archive 仅有 manifest/notes/patches，无 conanfile.py。
2.62.3 需从零编写完整 Conan recipe。

## 源码核验

- URL: `https://download.gnome.org/sources/librsvg/2.62/librsvg-2.62.3.tar.xz`
- SHA-256: `7eb449b2722a768021356f66dfee3202c229b54ed4e6a70ce40c090e97ff16f2`
- 设备端实测 sha256sum 与参考值（Solus）完全一致。

## 补丁

复用 2.62.2 的两个 HMDFS workaround patches（已验证 patch --dry-run -p1 通过）：

1. **0001-meson.build.patch**: `makedef = find_program('meson/makedef.py', native: true)` → 改用 `python3_native` + `makedef_script`，因为 HMDFS 禁止直接执行 Python 脚本。
2. **0002-rsvg-meson.build.patch**: `rsvg/meson.build` 中 `makedef_args = [makedef, ...]` → 改用 `[python3_native, makedef_script, ...]`。

## 依赖

所有依赖已在制品仓 ohpcd 可解析：
- cairo/1.18.4, glib/2.84.0.1, gdk-pixbuf/2.44.6
- pango/1.56.4, harfbuzz/14.2.0.1, libxml2/2.15.3.1
- fontconfig/2.18.1.1, freetype/2.14.3

## 构建配置

- meson + cargo-c（Rust 核心 + C API）
- 静态库构建（`--default-library=static`）
- 上游测试真实运行（conanfile build() 调 meson test）：C API tests + Rust tests (rsvg/librsvg) 三套件 round-9 全部 OK
  - C API 测试：LD_LIBRARY_PATH 注入（含 pixman，meson 编译 api 的 RUNPATH 缺传递依赖 libdirs）
  - Rust 测试：RUSTFLAGS rpath（RUNPATH 指向依赖 libdirs，避免 LD_LIBRARY_PATH 污染构建期 lld）
  - doctest 排除（patch 0003 `--tests`）：OHOS rust 工具链缺 rustdoc 组件
- 禁用 rsvg-convert（`-Drsvg-convert=disabled`）
- 禁用 introspection（`-Dintrospection=disabled`）
- 禁用 AVIF（`-Davif=disabled`）

## 测试

test_package 实质调用 librsvg C API：
- `rsvg_handle_new_from_data()` 解析最小 SVG
- `LIBRSVG_VERSION_STRING` 版本常量编译核验

上游测试运行说明（MANIFEST.yml 已声明 upstream_test_in_build: true）：
- cargo test（rsvg/tests/*.rs 12+ 文件 + src/test_utils）：经 meson cargo_wrapper.py 运行，RUSTFLAGS rpath 保证运行时 .so 可达
- C API tests（librsvg-c/tests-c/api.c）：LD_LIBRARY_PATH 注入保证 pixman 等传递依赖可达
- 修复链：round-5（patch 手写格式被拒）→ round-6（env dict 断言）→ round-7（C API 缺 pixman RUNPATH）
  → round-8（patchelf 破坏 OHOS 签名，WriteCodeSignBlock error，弃用）→ round-9（拆分方案）PASS
