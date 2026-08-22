# agg 2.7.0.r145 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-05
- 编译器: clang/clang++
- 状态: published

## 编译步骤

dfsg orig tarball 缺预生成的 configure/aux 文件，conanfile.py build() 用 autoreconf 链自动补齐：
libtoolize → aclocal → autoheader → autoconf → automake --add-missing → autoconf。
然后 patch configure 模板（HMDFS workaround），再 configure → make → make install。

configure 选项（最小核心库）：
--disable-examples --disable-ctrl --disable-platform --disable-freetype --disable-gpc --enable-static --disable-shared

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | AM_PATH_SDL undefined | OHOS 无 SDL m4 宏 | patch configure.ac 移除 SDL/FT2 autodetection |
| 2 | @am_AUTOM4TE@ not found | aclocal 占位符未替换 | Environment 注入 AUTOM4TE 绝对路径 |
| 3 | automake autoconf 127 | automake 硬编码不存在 autoconf | Environment 注入 AUTOCONF/AC_AUTOCONF |
| 4 | libtoolize sed 127 | libtoolize 硬编码不存在 sed | Environment 注入 SED=/usr/bin/sed |
| 5 | config.status Permission denied | HMDFS 拒 700 权限子目录写入 | patch configure: umask 077 mktemp → umask 022 mkdir |
| 6 | cc: not found | configure 默认查 cc | conan profile 已设 clang，autoreconf 后 configure 正常 |

## 源码修改

patches/0001-configure.ac.patch — 移除 AM_PATH_SDL / PKG_CHECK_MODULES(FREETYPE) 调用段
（OHOS 无 SDL m4 宏 + --disable-sdl/--disable-freetype 时不需要检测）

## 依赖版本

无外部依赖（所有可选层已禁用）

## 验证结果

conan create + test_package 通过：
  1/1 Test #1: test_agg Passed (0.06 sec)

test.cpp 实质测试 agg::pod_array<int>（构造、operator[]、size()），R34 合规。

## 注意事项

- dfsg tarball 的 config.guess/config.sub 是空文件，autoreconf 的 automake --add-missing 会自动补齐自带版本
- conan profile 的 os=OHOS 让 AutotoolsToolchain 自动处理平台识别
- HMDFS 平台限制：mktemp -d 创建 700 权限子目录拒写，需 patch configure 改 umask 022
---

**编译结束**: 2026-08-05 18:38
**最终状态**: published
