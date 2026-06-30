# cairo 1.18.2 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 设置环境变量：TMPDIR=/data/storage/el2/base/cache
2. meson setup builddir --prefix=/storage/Users/currentUser/usr/local --buildtype=release -Dxlib=disabled -Dxcb=disabled -Dfontconfig=disabled
3. meson compile -j4
4. meson install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译失败：FC_HINT_FULL 等常量未定义 | fontconfig 未安装，xlib 后端需要 fontconfig | 禁用 xlib/xcb/fontconfig 后端 |

## 源码修改

无补丁。cairo 1.18.2 已移除 GL/GLES 后端，直接使用 meson 构建。

## 依赖版本

- pixman: 0.46.4
- freetype2: 26.6.20
- libpng: 1.6.43
- glib-2.0: 2.88.0
- zlib: 1.3.1

## 验证结果

```bash
pkg-config --modversion cairo
1.18.2
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libcairo.so.2.11802.2 | 1.8MB | 核心库 |
| libcairo-gobject.so.2.11802.2 | 4.0MB | GObject 绑定 |
| libcairo-script-interpreter.so.2.11802.2 | 174KB | 脚本解释器 |

## 注意事项

1. cairo 1.18.2 已移除 OpenGL/GLES 后端，无需 -Dgl-backend=disabled 等选项
2. 如果需要 xlib/xcb 支持，需要先安装 fontconfig
---

**编译结束**: 2026-05-29 22:14
**最终状态**: built
