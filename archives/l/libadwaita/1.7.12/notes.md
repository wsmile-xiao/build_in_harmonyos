# libadwaita 1.7.12 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤
1. conan create（G2 conan-verify，--build=missing）主包构建成功
2. appstream 链 13 包（libxmlb 等）因 glib override 到 2.84.0.1.1 需按新配置从源码重建（制品仓二进制不匹配）
3. test_package 消费者构建 + meson test 通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 构建环境 `env python3` 解析到 hnp python3.12，被 glib 包 libintl（仅 g_libintl_* 前缀）干扰，libxmlb 重建失败 | conan buildenv PATH 前置 hnp/bin；hnp python 需标准 libintl_gettext 符号，glib 包 libintl.so.8 只有 g_ 前缀（proxy-libintl） | 本机 profile 交换 buildenv PATH 顺序让 usr/local/bin 排最前，构建环境 python 解析到完整 3.12.9 |
| 2 | msgfmt 生成 po 翻译时报 libintl 符号缺失 | usr/local/bin/msgfmt 需标准 libintl，被 glib 包 libintl 干扰 | 本机 msgfmt wrapper 前置 usr/local/lib 再 exec 真 msgfmt（仅影响 msgfmt 单进程） |
| 3 | PkgConfigDeps 报 `Component 'glib::gobject' not found in 'glib'` | libxmlb 组件 requires 引用 glib::gobject 旧名，glib/2.84.0.1.1 组件键为带 -2.0 后缀（gobject-2.0 等） | generate() 为 glib 依赖 cpp_info 注入无后缀组件别名（glib/gobject/gio/gmodule），appstream 配方同款注入先例 |
| 4 | 链接 libadwaita-1.so 时 g_libintl_* 符号未定义 | glib 包内真实 glib-2.0.pc 带 `-lintl`（glib 包自带 libintl.so.8 导出 g_libintl_*，E142 proxy-libintl），conan PkgConfigDeps 生成的 pc 缺 `-lintl` | `_fix_glib_pc_intl()`：给 conan 生成的 glib-2.0.pc 的 Libs 追加 `-lintl` |
| 5 | test_package generate() 再报 `glib::gobject` 组件缺失 | 主包修复后 test_package 独立 generate() 仍需同款别名注入 | test_package generate() 同样注入 glib 无后缀组件别名 |

## 源码修改
- 无补丁（conanfile.py 内 generate() 逻辑修复：glib 组件别名注入 + glib-2.0.pc -lintl）

## 依赖版本
- gtk4/4.22.4、glib/2.84.0.1.1（override 固定）、appstream/1.2.0、pango/1.56.4（override）、zstd/1.5.7.1（override）、fribidi/1.0.16、zlib/1.3.1.1、fontconfig/2.18.1.1、sassc/3.6.2（tool_requires）

## 验证结果
- G2 conan-verify PASS（本机 profile + 默认 profile 均通过）
- G3/G4 PASS

## 注意事项
- libadwaita 1.7.12 硬依赖 appstream（AdwAboutDialog 读 AppStream 元数据），glib_min>=2.80、gtk_min>=4.17.5
- glib/2.84.0.1.1 的 bin 工具（glib-compile-resources 等）需 re-sign（.codesign 陈旧，OHOS XPM exec 拒绝）且 LD_LIBRARY_PATH 前置 glib lib（无 RPATH），见 `_prepend_glib_bin_to_path`
- 本机验证环境修复（profile/wrapper）仅限本机，不入 PR；配方修复（组件别名、-lintl）为通用修复
---

**编译结束**: 2026-09-29 00:38
**最终状态**: published
