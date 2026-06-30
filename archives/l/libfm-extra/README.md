# libfm-extra

Libfm-extra 是一个轻量级的 XML 文件处理库，独立于 GTK 和完整的 libfm 包。

## 描述

libfm-extra 提供了以下功能：
- XML 文件解析和生成
- 基于 GObject 的类型系统
- 简单的 XML DOM 操作接口

该库是 libfm（文件管理库）的独立组件，不依赖 GTK，适合需要 XML 处理功能的项目。

## 版本信息

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.3.2 | built | 2026-06-05 |

## 编译配置

- 构建系统: autotools
- configure 参数: `--with-extra-only --disable-nls`
- 依赖: glib-2.0, libintl_glib

## 使用说明

安装后使用 pkg-config 获取编译参数：

```bash
pkg-config --cflags libfm-extra
pkg-config --libs libfm-extra
```

链接时需要添加 `-lintl_glib` 以解决 g_libintl_* 符号依赖。

## 参考

- 源码: http://deb.debian.org/debian/pool/main/libf/libfm/
