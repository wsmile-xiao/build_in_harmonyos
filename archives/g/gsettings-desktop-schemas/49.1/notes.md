# gsettings-desktop-schemas 49.1 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 GNOME 官方下载源码 tarball
2. 使用 meson 配置：`meson setup build --prefix=$DEFAULT_PREFIX -Dintrospection=false`
3. 使用 ninja 构建：`ninja -C build`
4. DESTDIR 安装：`DESTDIR=$TEST_PREFIX ninja -C build install`
5. staging 验证通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | glib-mkenums 执行失败 | Perl 脚本 shebang `#!/usr/bin/perl` 路径不存在 | 创建 wrapper 脚本 `/usr/local/bin/glib-mkenums`，修正 shebang 为 `#!/data/service/hnp/bin/perl` |
| 2 | 缺少 gobject-introspection | 依赖缺失 | 禁用 introspection：`-Dintrospection=false` |
| 3 | meson 找不到 clang | PATH 未包含 /data/service/hnp/bin | 配置 CC/CXX 为完整路径，PATH 加上 hnp bin 目录 |

## 源码修改

无补丁，纯数据/头文件包安装。

## 依赖版本

- meson: 1.11.1
- ninja: 1.13.1
- glib-mkenums: 2.38.2 (via HNP)
- pkg-config: 0.29.2

## 验证结果

```bash
$ pkg-config --modversion gsettings-desktop-schemas
49.1
$ pkg-config --cflags gsettings-desktop-schemas
-I/storage/Users/currentUser/usr/local/include/gsettings-desktop-schemas
```

## 交付物

| 文件 | 说明 |
|------|------|
| headers/gdesktop-enums.h | C 头文件，定义桌面枚举类型 |
| schemas/*.gschema.xml | GNOME 桌面 GSettings schemas (32 个) |
| gsettings-desktop-schemas.pc | pkg-config 文件 |
| po/*.mo | 国际化翻译文件 (48 种语言) |

## 注意事项

1. gsettings-desktop-schemas 是纯数据/头文件包，无可执行二进制
2. 必须禁用 introspection 选项（无 gobject-introspection 预编译包）
3. pkg-config 文件正确，头文件路径包含 gsettings-desktop-schemas 子目录
4. schemas 文件安装到 share/glib-2.0/schemas，需配合 glib-compile-schemas 使用
5. glib-mkenums 是 Perl 脚本，需要 perl 在 PATH 中或使用 wrapper

---
**编译结束**: 2026-08-06
**最终状态**: built
---

**编译结束**: 2026-08-06 15:58
**最终状态**: built
