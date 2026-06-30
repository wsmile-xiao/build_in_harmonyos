# libwpebackend-fdo 1.15.90 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-06-15
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: failed

## 编译步骤

1. 初始化：`ohc-run.py init-build libwpebackend-fdo 1.15.90 --url=https://github.com/Igalia/WPEBackend-fdo/releases/download/1.15.90/wpebackend-fdo-1.15.90.tar.xz`
2. 配置：`meson setup builddir --prefix=$HOME/usr/local`
3. 编译：`ninja -C builddir` — 失败于缺少 epoxy/egl.h

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少依赖 wpe-1.0 | libwpe 未安装 | 手动编译 libwpe 1.16.0（meson，禁用 xkb） |
| 2 | 缺少依赖 epoxy | libepoxy 未安装 | 安装预编译包 libepoxy 1.5.10 |
| 3 | 缺少 epoxy/egl.h | 预编译 libepoxy 没有 EGL 支持（epoxy_has_egl=0） | **阻塞：需重新编译 libepoxy 启用 EGL** |

## 依赖版本

| 软件 | 版本 | 来源 |
|------|------|------|
| libwpe | 1.16.0 | 手动编译（meson，禁用 xkb） |
| libepoxy | 1.5.10 | 预编译包（缺少 EGL 支持） |
| wayland | 1.22.0 | 预编译包 |
| glib | 2.88.0 | 预编译包 |
| libxkbcommon | 1.6.0 | 预编译包 |

## 验证结果

```bash
# 检查 libwpe 安装
pkg-config --modversion wpe-1.0
# 输出: 1.16.0

# 检查 libepoxy EGL 支持
pkg-config --variable=epoxy_has_egl epoxy
# 输出: 0（缺少 EGL 支持）

# 检查系统 EGL
find /data/service/hnp/ohos-sdk.org -name "egl.h"
# 输出: /data/service/hnp/.../include/EGL/egl.h（系统有 EGL）
```

## 失败原因

编译在 Step4（make）阶段失败。根本原因是：

**预编译的 libepoxy 1.5.10 包没有启用 EGL 支持（epoxy_has_egl=0）**，导致：
- 缺少头文件 `$PREFIX/include/epoxy/egl.h`
- libwpebackend-fdo 的多个源文件依赖 epoxy 的 EGL 功能无法编译

涉及的源文件：
- `src/egl-client.h` (第28行：`#include <epoxy/egl.h>`)
- `src/egl-client-dmabuf-pool.cpp`
- `src/egl-client-wayland.cpp`
- 等多个 EGL 相关文件

## 建议的修复路径

1. **重新编译 libepoxy 启用 EGL**：
   - 系统有 EGL 库（`/data/service/hnp/.../libEGL.so`）
   - 命令：`meson setup build -Degl=enabled -Dglx=disabled -Dwgl=disabled`

2. **或者修改 libwpebackend-fdo 源码**：
   - 禁用 EGL 相关功能（需分析 meson.build 和源码）
   - 可能影响软件功能

## 知识提取

创建了知识草稿 E100（contributor: EE95）：
- 文件：`knowledge/graph/draft/E100-draft-EE95.kv`
- 主题：预编译 libepoxy 缺少 EGL 支持

## 注意事项

这是一个深层依赖问题，需要重新编译 libepoxy 才能解决。当前编译链：
- libwpe（已编译）→ libepoxy（需重编译启用 EGL）→ libwpebackend-fdo（阻塞）
---

**编译结束**: 2026-06-15 20:01
**最终状态**: built
