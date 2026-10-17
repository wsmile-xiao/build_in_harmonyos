# gom 0.5.4 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-15
- 编译器: clang/clang++ (OHOS aarch64)
- 状态: built

## 编译步骤

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方使用 MesonToolchain + PkgConfigDeps：
- `enable-introspection=false`：跳过 GIR 生成（无需 gobject-introspection 工具链）
- `enable-gtk-doc=false`：跳过文档
- `wrap_mode=nodownload`：禁止 meson subproject 下载
- glib .pc 文件注入 glib_mkenums/genmarshal 变量与 `-lintl`（同 json-glib 模式）
- meson native 文件注入 ar/ranlib/pkg-config 路径

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | download.gnome.org 连接被重置 | 网络瞬时失败 | conandata 增加 ftp.gnome.org mirror_url，source() 失败自动回退 |
| 2 | 顶层 meson.build 无条件依赖 gdk-pixbuf-2.0 | gom 顶层直接 `dependency('gdk-pixbuf-2.0')`（仅 test-gom-transform 使用） | requirements 增加 gdk-pixbuf/2.44.6（已发布） |

## 依赖版本

- glib/2.84.0.1（提供 glib-2.0/gobject-2.0/gio-2.0，>= 2.38 满足）
- sqlite3/3.49.1（>= 3.7 满足）
- gdk-pixbuf/2.44.6

## 验证结果

- conan create 构建 libgom-1.0.so + 头文件 + gom-1.0.pc
- 上游测试：13 个 meson test 入口（tests/test-gom-*.c）
- 消费者测试：test_package/test.c 通过公开 API 打开内存 SQLite、建表、插入、游标回读

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Meson 配方（shared library） |
| conandata.yml | 官方源码 URL + SHA256 |
| test_package/ | 真实消费者测试（SQLite 内存库 DDL/DML + 游标断言） |
| manifest.yaml / notes.md | 编译元数据 |

## 注意事项

- gom 是 GNOME GObject 库（LGPL-2.1+），产物 libgom-1.0.so、include/gom-1.0/gom/、gom-1.0.pc
- 无补丁（patches_applied: []）
---

**编译结束**: 2026-08-15 22:30
**最终状态**: built
