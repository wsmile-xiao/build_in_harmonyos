# btparse — 软件包说明

## 概述

btparse 是一个解析 BibTeX 文件的 C 库，由 Greg Ward 开发（1997-2005），后由 Alberto
Manuel Brandão Simões (AMBS) 维护并作为 Text-BibTeX 的 C 层发布在 CPAN。本包适配
上游 0.35 正式源码包（2005-10-25 发布）。

- 库名：`libbtparse`（libtool -version-info 0:0:0 → `libbtparse.so.0.0.0`）
- 公共头：`btparse.h`
- 解析器由 PCCTS 1.33 生成；**生成物（bibtex.c/scan.c 等）随 tarball 发布**，
  构建不需要 `antlr`/`dlg` 工具
- 许可：LGPL-2.0-or-later（COPYING 为 GNU LGPL v2）

## OHOS 适配要点（0.35）

| 问题 | 修复 | 知识条目 |
| --- | --- | --- |
| config.guess 不识别 HarmonyOS | 注入 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos` | E007 |
| 2005 版 config.guess 临时目录 umask 077 在 HMDFS setgid 下属主不可写 | umask 077 → 022 | E011/E129/E136/E206 |
| 2005 版 config.sub 无 aarch64、不识别 ohos | 参数解析后插入 aarch64 linux/ohos 早退 case | E072 |
| configure/config.status confstat 临时目录同 umask 问题 | umask 077 → 022 | E011/E136/E206 |

注意：`scripts/patch-autotools-ohos.pl` 面向新版 config.guess/sub 设计，对 2005 年代
文件仅部分命中（config.guess 注入的是新版 `GUESS=` 风格，老版本每个分支需 `echo …; exit`
直接输出）。本包补丁为按 2005 版文件结构手工等价改写。

## 构建

- 构建系统：Autoconf 2.57 + Automake + libtool 1.5.18
- Conan 配方：`archives/b/btparse/0.35/conanfile.py`（AutotoolsToolchain，
  默认 `--enable-static --disable-shared`）
- 上游测试：`make check`（tests/TESTS = read_test simple_test postprocess_test）
- 设备验证：OHOS 6.0 / aarch64 / clang 15.0.4，`conan create` + test_package 通过

## 安装产物

- `lib/libbtparse.so.0.0.0`（+ `.so.0` 符号链接）或静态库
- `include/btparse.h`
- `bin/bibparse` — BibTeX 语法检查器（上游唯一安装的命令行工具；
  biblex/dumpnames 为上游 noinst_PROGRAMS，不安装）
- `lib/pkgconfig/btparse.pc`

## 测试统计口径

- 上游：3 个测试程序（automake TESTS），断言总数 75 =
  read_test 13（CHECK 宏静态计数）+ simple_test 36（ok 实例行）+
  postprocess_test 26（参数化实例行）
- 上游 tests/ 中 macro_test/case_test/name_test/purify_test 为上游明确声明的
  交互式测试（不在 TESTS），上游默认口径即不执行
- test_package：1 个消费者程序，18 项断言

## 上游

- 源：CPAN `authors/id/A/AM/AMBS/btparse/btparse-0.35.tar.gz`
- 项目主页：https://github.com/ambs/Text-BibTeX（CPAN 发行物 Text-BibTeX 的 C 库层）
