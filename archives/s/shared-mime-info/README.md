# shared-mime-info

## 简介

shared-mime-info 是一个用于共享 MIME 类型信息的数据库和相关工具。它提供了一个中央数据库，用于存储文件类型和 MIME 类型的映射关系，被许多桌面环境和应用程序使用。

## 主要功能

- **update-mime-database**: 用于更新 MIME 类型数据库的工具
- **freedesktop.org.xml**: 标准的 MIME 类型定义文件
- **shared-mime-info.pc**: pkg-config 文件，用于其他软件查找依赖

## 版本信息

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 2.4 | published | 2026-05-28 | 使用 g_libintl_shim 解决链接问题 |

## 依赖

- glib 2.88.0
- libxml2 2.12.10

## 编译说明

在鸿蒙系统上编译时，需要添加 `g_libintl_shim.a` 静态库来解决 glib 的国际化依赖问题。

```bash
meson setup builddir --prefix=$DEFAULT_PREFIX \
  -Dbuild-tools=true \
  -Dbuild-translations=true \
  -Dbuild-tests=false
ninja -C builddir
ninja -C builddir install DESTDIR=$TEST_PREFIX
```

## 补丁说明

- `0001-.pre-scan-report.yaml.patch`: 预扫描报告（自动生成）
- `0002-src-meson.build.patch`: 添加 g_libintl_shim 链接参数（平台适配）