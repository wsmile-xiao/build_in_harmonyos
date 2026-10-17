# libuninameslist

## 简介

libuninameslist 是 fontforge 生态的 Unicode 字符名表库：将 Unicode
官方 NamesList.txt 注释数据编译为 C 静态数据表（nameslist.c），提供
三个公开 API——`uniNamesList_name(uni)` 返回字符官方名称（如
"GREEK SMALL LETTER LAMDA"）、`uniNamesList_annot(uni)` 返回注释块
（别名、交叉引用等）、`uniNamesList_NamesListVersion()` 返回数据版本
横幅。任何需要 Unicode 字符元数据的字体/文本工具均可链接使用。

## 上游信息

- 官方仓库: https://github.com/fontforge/libuninameslist
- License: 数据表为 Unicode Terms of Use（nameslist.c 头部声明）；
  构建 tooling（buildnameslist.c）为 GPL-2.0-or-later
- 构建系统: Autotools（tag 归档不含生成的 configure，需
  autoreconf -f -i 引导）

## 上游测试

上游 `Makefile.am` 未注册任何 `TESTS` / `check_PROGRAMS` / 自定义
check 目标：`make check` 输出 "Nothing to be done for 'check'"
（automake 默认零测试审计目标，exit 0）。可选的 buildnameslist 程序
（EXTRA_PROGRAMS）是数据表再生成工具，非测试。上游 C 可运行测试
= 0。消费者级验证见各版本 `test_package/`。

## OHOS 适配

- 2013 年版 config.guess/config.sub 不识别鸿蒙三元组（E007/E514），
  配方显式钉死 `--build/--host=aarch64-unknown-linux-ohos`
- tag 归档无 configure：`autoreconf -f -i` 引导（E443：autotools
  闭包由 tool_requires automake/1.18 + libtool/2.5.4 补齐）
- HMDFS：configure umask 077 改写（E114）、make -j1（E074）
- 零源码补丁，全部运行时处理（同 libantlr3c/3.5.3 策略）

详见各版本目录 `notes.md` 与 `manifest.yaml`。

## 依赖

无第三方运行时依赖：纯 C 数据表 + 二分查找，仅 libc。

## 版本

| 版本 | 状态 |
|------|------|
| 0.3.20130501 | built（配方 + test_package 已验证，待 PR） |
