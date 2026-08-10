# libgcab 1.6 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-10
- 编译器: clang/clang++
- 状态: published (conan create + test_package passed)

## 源码
- URL: https://gitlab.gnome.org/GNOME/gcab/-/archive/v1.6/gcab-v1.6.tar.gz
- SHA256: cda7b2cbf3967ff9c48e75afb86ee683d98ad8fb2d9a4a966a9e10cfdb349886

## 依赖
- glib/2.84.0 (gio-2.0, glib-2.0, gobject-2.0 等)
- zlib/1.3.1
- libffi/3.4.4 (glib 间接依赖)
- pcre2/10.40 (glib 间接依赖)

## 配置选项
- -Dintrospection=false: 禁用 GObject Introspection
- -Dvapi=false: 禁用 Vala 绑定
- -Ddocs=false: 禁用文档
- -Dnls=false: 禁用 Native Language Support (HarmonyOS 无 gettext/libintl)

## 补丁
1. 0001-static-library-for-gio-type-system.patch:
   - 将 shared_library 改为 static_library
   - 原因: HarmonyOS 平台 glib 为静态库，共享库内嵌 gio 静态库会导致 GObject 类型系统冲突
   - 移除 version, darwin_versions, link_args, link_depends (仅适用于共享库)

2. 0002-add-gettext-stubs-for-ohos.patch:
   - 在 src/gcab.c 中添加 gettext/textdomain/bindtextdomain 等 stub 宏定义
   - 原因: HarmonyOS 无 libintl/gettext，_() 宏需要这些函数

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 配置失败: 缺少 gobject-introspection-1.0 | 默认启用 introspection | -Dintrospection=false |
| 2 | 编译失败: gettext 未声明 | HarmonyOS 无 libintl | 添加 gettext stub 宏定义 |
| 3 | 链接失败: 缺少 libffi, libpcre2-8 | glib pkg-config 引用但路径未包含 | conan PkgConfigDeps 生成 .pc 文件 |
| 4 | meson 找不到 gio-2.0 | glib 包只有一个 glib-2.0.pc | 生成 gio-2.0.pc wrapper (Requires: glib-2.0) |
| 5 | meson 找不到 glib-mkenums | glib-2.0.pc 缺少 glib_mkenums 变量 | 向 .pc 文件追加 glib_mkenums 变量 |
| 6 | 测试链接失败: gettext/dgettext 等未定义 | musl libc 无 gettext | 链接 -l:ld-musl-aarch64.so.1 |

## 验证结果

### conan create
```
libgcab/1.6@ohpcd/stable: All tests passed
PASS: gcab_cabinet_new() succeeded
PASS: GCAB_IS_CABINET check passed
```

## 交付物
- conanfile.py: Conan 配方
- conandata.yml: 源码和补丁数据
- test_package/: 测试包
- patches/: 2 个补丁文件
---

**编译结束**: 2026-08-10 06:17
**最终状态**: built
