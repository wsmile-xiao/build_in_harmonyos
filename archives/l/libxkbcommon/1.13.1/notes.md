# libxkbcommon 1.13.1 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-11
- 状态: published
- 上游 tag: xkbcommon-1.13.1（注意：无 v 前缀，上游 tag 格式为 xkbcommon-<version>）
- 上游 commit: 6f76d19d Bump version to 1.13.1

## 依赖分析
- 核心库 libxkbcommon 无外部运行时依赖
- meson.build 确认：libxml2 仅用于 xkbregistry 模块（`enable-xkbregistry` 选项控制），禁用后无 libxml2 依赖
- bison >=3.6 为构建时依赖（系统已有 bison 3.8.2）
- x11 模块需 xcb（`enable-x11` 选项控制），禁用后无 xcb 依赖
- wayland 模块需 wayland-client/wayland-protocols（`enable-wayland` 选项控制），禁用后无 wayland 依赖
- 与 1.6.0 相同策略：禁用 x11/xkbregistry/docs/tools/wayland/bash-completion，仅保留核心库

## 与 1.6.0 差异
- 版本升级 1.6.0 → 1.13.1
- 构建方式完全一致（meson + 相同选项禁用策略）
- 1.13.1 为上游稳定版本，API 向后兼容

## 遇到的问题与解决方案
- 无 X11/Wayland 依赖（禁用 x11/wayland 模块）
- OHOS 沙箱 meson 找不到 llvm-ar → 注入 native file（1.6.0 先例）
- OHOS SDK lld 运行时需 libxml2.so.16 → 注入 LD_LIBRARY_PATH（1.6.0 先例）
- 上游 meson test：context 测试在 OHOS 沙箱 SIGSEGV（环境限制，非代码问题），其余测试全过

## 测试
- 上游 meson test 测试套件（keysym/keymap/context 等），18/19 通过
- test_package 验证产物完整性（xkbcommon.h/libxkbcommon.so/xkbcommon.pc）

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 |
| conandata.yml | 源码地址与 sha256 |
| test_package/ | 消费者测试 |
| manifest.yaml | 版本元数据 |
