# libsvg 0.1.4 编译笔记

## 编译概述

**软件**: libsvg
**版本**: 0.1.4
**状态**: built（本地构建 + test_package 66 断言全过）
**日期**: 2026-09-01（构建）

## 背景

libsvg-cairo 0.1.6 阻塞：仓库与 ohpcd 制品仓均无 libsvg。本包完成后可解阻
libsvg-cairo（其 conanfile requires libsvg/0.1.4）。

## 源码核验

- URL: `https://cairographics.org/snapshots/libsvg-0.1.4.tar.gz`
- SHA-256: `4c3bf9292e676a72b12338691be64d0f38cd7f2ea5e8b67fbbf45f1ed404bc8f`
- 实测 sha256sum 与下载 tarball 完全一致（366688 字节）
- License: LGPL-2.1-or-later（源码 COPYING 为 LGPL-2.1，各 .c/.h 头部
  声明 "distributed under the terms of the GNU Lesser General Public License"）
- 发布时间：2003 年 cairographics snapshot（cairographics.org/snapshots/
  目录下与 libsvg-0.1.3、0.1.5 同期）

## 依赖（源码证据）

`configure.in` 无条件 `PKG_CHECK_MODULES(libxml-2.0 >= 2.4.7)`（默认且唯一
启用的解析后端；expat 仅是 configure.in 中注释掉的可选后端，未构建）。

| 依赖 | 证据 | 版本（ohpcd registry） |
| --- | --- | --- |
| libxml2 | configure.in PKG_CHECK_MODULES；svg_parser_libxml.c SAX API | 2.15.3 |
| libpng | svg_image.c 直接调用 png_create_read_struct 等 | 1.6.58 |
| libjpeg | svg_image.c 直接调用 jpeg_std_error 等 | 10 |
| zlib | svg.c svg_parse_file() gzopen/gzread/gzeof/gzclose 直接调用；libsvg.pc.in Libs 含 -lz | 1.3.1.1 |

## 补丁（6 个，全部 portability，不动 SVG 解析业务逻辑）

先零 patch 尝试：2003 源码在现代工具链下必然失败，沙盒取证后最小修复。
全部由 Conan patch backend（apply_conandata_patches）应用。

1. **0001-svgint.h-include-libxml-parser-context.patch**
   - 原错误: `svgint.h:40:9: error: unknown type name 'xmlParserCtxtPtr'`
   - 平台原因: libxml2 2.15 头文件自包含化，libxml/SAX.h 不再间接引入
     parser.h；svgint.h 依赖旧版传递包含
   - 修复: svgint.h 增加 `#include <libxml/parser.h>`
2. **0002-svg_parser_libxml.c-libxml-2.5-SAX-API.patch**
   - 原错误: `error: unknown type name 'xmlEntity'` / `'xmlSAXHandler'`
   - 平台原因: 同上，SAX2 时代起 SAX.h 不再导出这些类型
   - 修复: svg_parser_libxml.c 增加 `#include <libxml/parser.h>`
3. **0003-svg_color.c-include-stdlib.h.patch**
   - 原错误: `svg_color.c: implicit declaration of function 'bsearch'`
     （C89 源码 + clang-15 默认 C99 报错）
   - 修复: 增加 `#include <stdlib.h>`
4. **0004-svg_image.c-libpng-1.4-API.patch**
   - 原错误: `'png.h' file not found`（pkg-config 传 -I 后消失）及
     `png_check_sig`/`png_set_gray_1_2_4_to_8` 隐式声明
   - 平台原因: libpng 1.4 起删除 png_check_sig（改用 png_sig_cmp）、
     png_set_gray_1_2_4_to_8 改名 png_set_expand_gray_1_2_4_to_8
   - 修复: 两处 API 名替换（1:1 语义）
5. **0005-config.guess-config.sub-ohos.patch**
   - 原错误: 2003 版 config.guess 不识别 `uname -s = HarmonyOS`，输出
     `aarch64-unknown-linux-ohos` 以外的无效三元组；config.sub 拒绝
     aarch64 CPU 与 linux-ohos OS
   - 平台原因: 2003 年不存在 HarmonyOS
   - 修复: config.guess 增加 `aarch64:HarmonyOS:*:*` case；config.sub
     CPU 列表增加 aarch64、OS 列表增加 -linux-ohos*（含 kernel-os 分支）
6. **0006-configure-umask-022.patch**
   - 原错误: `configure: error: cannot run C compiled programs`——
     configure 内建 tmp 目录探测用 `umask 077 && mktemp -d`，鸿蒙
     MAC 拒绝该 0700 目录上的执行探测
   - 平台原因: HarmonyOS MAC 对 0700 mktemp 目录的限制
   - 修复: umask 077 → 022（与 a52dec 0002 同模式）

## 构建配置

- Autotools（AutotoolsToolchain + AutotoolsDeps + PkgConfigDeps）
- 静态库（--enable-static --disable-shared）
- `--host=aarch64-unknown-linux-ohos`（conanfile 按settings.os==OHOS 注入）
- compiler 从 profile `tools.build:compiler_executables` 获取（OHOS clang 15）
- 共享依赖（libxml2/libpng/libjpeg .so）通过 configure LDFLAGS 注入
  -Wl,-rpath 使 configure 探测程序可运行
- package() 后删除 libtool *.la
- package_info: libs=["svg"], pkg_config_name=libsvg,
  cmake_target_name=libsvg::libsvg（CMakeDeps 生成 libsvg::libsvg target）

## 上游测试核查（硬证据）

- tarball 完整文件列表无 test/tests/regression 目录、无 *.sh/*.pl/*.py
  测试脚本、无 .github/.gitlab-ci CI 配置
- src/Makefile.am: 仅 lib_LTLIBRARIES = libsvg.la + include 头安装，无
  TESTS / check_PROGRAMS
- 顶层 Makefile.am: 仅 SUBDIRS = src，无 TESTS
- `make check` 实际执行：`make: Nothing to be done for 'check'`（无目标）
- `make test` 实际执行：`make: *** No rule to make target 'test'`
- 上游测试数：**Total=0 Pass=0 Fail=0 Skip=0**

## test_package（消费者功能测试，66 断言）

程序化生成 SVG 文本（无外部 fixture），链接最终 Conan package 的 libsvg：

- test 1: 最小 `<svg>` — viewport(200x100)/viewBox(10 20 200 100)/
  svg_get_size 断言
- test 2: `<rect x=5 y=6 w=40 h=30 rx=2 ry=3 fill=#010203>` — 几何与
  颜色逐项断言
- test 3: `<path d="M 10 20 L 30 40 C ... 90 100 Z" stroke=#ff0000
  stroke-width=2.5>` — move/line/curve/close 几何 + stroke 颜色/宽度
- test 4: 分块解析（svg_parse_chunk_begin + 3 不等长 chunk + end）与
  整体解析结果一致性
- test 5 (负向): `<<badmarkup>` 致命语法错误 → 断言 SVG_STATUS_PARSE_ERROR
- test 5b (负向): `</xsvg>` tag mismatch → 断言 SVG_STATUS_PARSE_ERROR
  （注：错误前已完整解析的 rect 仍可渲染——上游流式行为，已记录）
- test 6 (负向): 纯文本垃圾输入 → 断言不返回 SUCCESS
- test 7 (负向): 不存在文件 → 断言 SVG_STATUS_FILE_NOT_FOUND

无 `|| true`、无 ignore_errors、无无条件 echo OK。

注意：libsvg 对 render engine 回调无 NULL 检查（svg_style.c 无条件
`engine->set_color` 等），测试引擎必须实现全部回调（含 begin_element/
end_element），否则 SIGSEGV。

## OHOS 真实性验证

libsvg_test（最终测试二进制）：
- `readelf -h`: Class: ELF64, Machine: AArch64, Type: DYN (PIE)
- `readelf -l`: Requesting program interpreter: /lib/ld-musl-aarch64.so.1
- `.comment`: `OHOS (dev) clang version 15.0.4`
- target triple: aarch64-unknown-linux-ohos（config.sub 认证）
- 本机（HarmonyOS PC, HongMeng Kernel 1.12.0 aarch64）真实执行通过
- libsvg 为静态库（.a），无 SONAME/symlink/NEEDED 问题
