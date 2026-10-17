# wayland 1.22.0.1 适配笔记

## 编译环境
- 构建系统: meson
- 上游版本: 1.22.0
- 适配版本: 1.22.0.1（R37: conandata.yml URL/SHA256 更正 + conanfile.py export_sources 补齐）
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
meson setup builddir --prefix=$DEFAULT_PREFIX --native-file native.ini \
  -Ddocumentation=false -Ddtd_validation=true -Dtests=true -Dscanner=true -Dlibraries=true
ninja -C builddir
meson test -C builddir
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 找不到 clang/llvm-ar | HMDFS 软链接在 meson subprocess 中解析失败 | 用 --native-file 指定完整路径 c/cpp/ar |
| 2 | ffi.h not found | libffi.pc prefix=/ → includedir=/include（不存在） | 修正 .pc prefix 指向实际包目录 |
| 3 | expat.h not found | expat.pc prefix 指向错误包目录 | 修正 .pc prefix 指向实际包目录 |
| 4 | 7/23 测试失败 | bind() Operation not permitted（OHOS 沙箱 socket 隔离） | 平台限制，非代码问题，不阻断构建 |

## 源码修改

无补丁。所有修改在 conanfile.py generate() 中处理（.pc prefix 修正 + native file 注入）。

## 依赖版本

- libffi/3.4.4
- expat/2.8.2
- libxml2/2.15.3

## 验证结果

上游测试 23 项：
- 通过: 16（array, client, event-loop, fixed, interface, list, map, signal, newsignal, message, resources, headers, os-wrappers, cpp-compile, scanner, wayland-egl symbols）
- 失败: 7（protocol-logger, socket, connection, compositor-introspection, queue, display, sanity）
  - 全部失败原因：bind() Operation not permitted（OHOS 沙箱 socket 隔离）
- 跳过: 0

## 交付物

- libwayland-server.so.0.22.0
- libwayland-client.so.0.22.0
- libwayland-cursor.so.0.22.0
- libwayland-egl.so.1.22.0
- wayland-scanner（可执行）

## 注意事项

- conanfile.py generate() 中 .pc prefix 修正是必需步骤（libffi/expat/libxml2 的 .pc prefix 不正确）
- meson native file 注入 ar 路径是必需步骤（HMDFS 软链接在 meson subprocess 中不可用）
- b_ndebug=false 必须设置（测试依赖 assert()，Release 构建默认 NDEBUG 会禁用 assert）
- XDG_RUNTIME_DIR 必须设置为可写目录（test-runner.c 需 mkdtemp）
---

**编译结束**: 2026-09-07 14:44
**最终状态**: built
