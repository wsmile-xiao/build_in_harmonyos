# cairomm

**描述**: Cairo 的 C++ 绑定库，提供 C++ 接口封装 cairo graphics library

**官网**: https://www.cairographics.org/cairomm/

**源码**: https://gitlab.freedesktop.org/cairo/cairomm

**许可证**: LGPL v2+

## 编译版本

| 版本 | 状态 | 构建系统 | 日期 |
|------|------|---------|------|
| 1.18.0 | built | meson | 2026-05-21 |

## ABI 系列

- **cairomm-1.0**: 版本 ≤ 1.14.z（用于 gtkmm-2.4 和 gtkmm-3.0）
- **cairomm-1.16**: 版本 ≥ 1.16.0（用于 gtkmm-4.0）

当前编译版本 1.18.0 属于 **cairomm-1.16** ABI 系列。

## 依赖

- cairo >= 1.14.0
- sigc++-3.0 >= 3.0.0
- pixman-1
- freetype2

## pkg-config 名称

- **主库**: `cairomm-1.16`
- **FreeType 模块**: `cairomm-ft-1.16`

## 使用方法

```bash
# 安装预编译包
curl -fsSL https://gitcode.com/.../install.sh | sh -s -- cairomm 1.18.0

# 验证安装
pkg-config --modversion cairomm-1.16

# 编译时使用
pkg-config --cflags cairomm-1.16
pkg-config --libs cairomm-1.16
```

## 编译选项

```bash
meson setup builddir --prefix=$HOME/usr/local \
  -Dbuild-examples=false \
  -Dbuild-tests=false
ninja -C builddir
meson install
```

## 功能限制

当前 cairo 为静态库版本，部分功能受限：
- cairo-png 模块不可用（write_to_png）
- cairo-pdf 模块不可用
- cairo-svg 模块不可用

## 归档位置

```
archives/c/cairomm/
├── README.md (本文档)
├── manifest.yaml (软件级元数据)
└── 1.18.0/
    ├── manifest.yaml (版本级元数据)
    ├── notes.md (编译笔记)
    ├── packaging/ (预编译包)
    └── reports/ (构建报告)
```