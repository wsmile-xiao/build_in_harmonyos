# gsettings-desktop-schemas 49.1 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-20
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 GNOME 官方下载源码 tarball
2. 使用 meson 配置：`meson setup build --prefix=$DEFAULT_PREFIX -Dintrospection=false`
3. 使用 ninja 构建：`ninja -C build`
4. DESTDIR 安装：`DESTDIR=$TEST_PREFIX ninja -C build install`
5. staging 验证通过
6. 制作预编译包：`ohc-run.py package`
7. 本地安装：`ninja -C build install`（glib-compile-schemas 因权限问题未执行，手动验证 pkg-config 通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah URL 404 | Savannah 无此版本 | 使用 GNOME 官方 URL：download.gnome.org |
| 2 | 缺少 gobject-introspection | 依赖缺失 | 禁用 introspection：`-Dintrospection=false` |
| 3 | glib-compile-schemas 权限拒绝 | ELF 未签名/安全弹窗 | 手动验证 pkg-config 通过，schemas 已安装 |

## 源码修改

无补丁，纯数据包安装。

## 依赖版本

- meson: 1.11.0
- ninja: 1.13.2
- glib-mkenums: 已安装
- pkg-config: 0.29.2

## 验证结果

```bash
$ pkg-config --modversion gsettings-desktop-schemas
49.1
$ pkg-config --cflags gsettings-desktop-schemas
-I/storage/Users/currentUser/usr/local/include/gsettings-desktop-schemas
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| gsettings-desktop-schemas-49.1-ohos-aarch64.tar.gz | 1738KB | 预编译包 |

## 注意事项

1. gsettings-desktop-schemas 是纯数据/头文件包，无可执行二进制
2. 必须禁用 introspection 选项（无 gobject-introspection 预编译包）
3. pkg-config 文件正确，头文件路径包含 gsettings-desktop-schemas 子目录
4. schemas 文件安装到 share/glib-2.0/schemas，需配合 glib-compile-schemas 使用

---
**编译结束**: 2026-05-20 22:51
**最终状态**: built