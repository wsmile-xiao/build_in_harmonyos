# libgcab

## 简介

libgcab 是一个用于创建和读取 Microsoft Cabinet (.cab) 文件的库。它提供了简单的 API 来处理 Cabinet 归档文件，支持压缩和解压缩操作。

## 功能特性

- 创建和读取 Cabinet (.cab) 文件
- 支持压缩和解压缩
- 与 GLib/GObject 集成
- 提供命令行工具 `gcab`

## 编译版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 1.6 | built | 2026-06-05 |

## 编译说明

### 构建系统
- Meson

### 编译选项
- `-Dintrospection=false` - 禁用 GObject Introspection（cmd-pkgs 中无预编译包）
- `-Dvapi=false` - 禁用 Vala 绑定
- `-Ddocs=false` - 禁用文档生成

### 依赖
- gio-2.0 >= 2.88.0
- glib-2.0 >= 2.88.0
- zlib >= 1.3.1
- meson >= 1.11.1
- ninja >= 1.13.1

### 注意事项
1. 必须禁用 introspection 功能，否则需要 gobject-introspection 依赖
2. 所有 ELF 文件（二进制和库）都需要签名才能在鸿蒙系统上执行
3. 测试套件中部分测试失败（GFile 创建问题），但不影响库的编译和使用

## 使用方法

```bash
# 查看版本
gcab --version

# 创建 cabinet 文件
gcab -c archive.cab file1 file2

# 提取 cabinet 文件
gcab -x archive.cab

# 列出 cabinet 文件内容
gcab -l archive.cab
```

## 项目信息

- **上游地址**: https://download.savannah.nongnu.org/releases/libgcab/
- **许可证**: LGPL-2.1-or-later
- **维护状态**: 活跃维护

## 相关链接

- [项目主页](https://wiki.gnome.org/msitools)
- [GitLab 仓库](https://gitlab.gnome.org/GNOME/gcab)