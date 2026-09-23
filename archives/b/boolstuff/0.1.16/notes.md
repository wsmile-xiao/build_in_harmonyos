# boolstuff 0.1.16 — OHOS 适配笔记

- 适配日期:2026-09-05
- 设备:HarmonyOS PC(aarch64),`uname -s = HarmonyOS`,内核 HongMeng 1.12.0
- 工具链:clang 15.0.4、GNU Make 4.4.1、Python 3.12.8、Conan 2.29.1、Perl 5.44(IPC::Open2 可用)
- 上游:BoolStuff 0.1.16(Pierre Sarrazin),autotools 构建,C++ 库 + booldnf 命令
- 源码:Debian pool 权威镜像(上游 sarrazip.com 已失效:HTTPS 连接失败、HTTP 302 死链)
  - URL:`https://deb.debian.org/debian/pool/main/b/boolstuff/boolstuff_0.1.16.orig.tar.gz`
  - SHA-256:`c07211da584eb78501a2838e4fe19ee284acb6989dd89db7f86f88c3fdb21e83`
  - 与 `boolstuff_0.1.16-1.dsc` 的 Checksums-Sha256 逐字一致

## 1. 原生探索与三条根因

### 1.1 config.guess 无法识别 HarmonyOS

- 第一条真实错误:`configure: error: cannot guess build type; you must specify one`
- 根因:tarball 自带 config.guess/config.sub 为 2016-05 版,`UNAME_SYSTEM=HarmonyOS` 无匹配分支
- 修复:显式 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`(OHOS 用户态与 Linux 兼容,build==host 保持原生构建语义),不改任何生成物

### 1.2 toybox sed 对非法 UTF-8 字节的正则匹配失败

- 第二条真实错误:`configure: error: could not make ./config.status`(发生在 AC_OUTPUT)
- 定位过程:mksh 下逐步复现 autoconf 变量分解循环 → dump conf$$subs.awk → bash 逐行 `sed -n "s/.*%!_!# \$/X/p"` 对比 → 唯一失败行 64:`PACKAGE_SUMMARY_FR!Librairie calculant la forme normale disjonctive bool<0xE9>nne%!_!# `
- 最小复现:`printf 'ab\xe9%!_!# \n' | sed -n '/%!_!# \$/p'` 在 toybox sed(/usr/bin/sed → toybox)下无匹配;同输入 grep 正常;LC_ALL=C 不改变行为
- 机制:toybox sed 在 UTF-8 模式把 0xE9 当多字节序列首字节并吞掉后续 3 字节,`%!_!# ` 被吞后字面量残缺,匹配失败。129 个替换变量中恰好 1 个(PACKAGE_SUMMARY_FR)含 Latin-1 é,循环计数 128≠129,五轮耗尽报错
- 修复:将 configure.ac 与 configure(上游 tarball 分发形式自带、无 autoreconf 环境下的正式生成物)从 Latin-1 转换为 UTF-8。`boolstuff-0.1.spec.in` 实测已是 UTF-8 无需修改;`boolstuff-0.1.spec` 为 config.status 生成物,不进补丁
- 上游注释自标 "# UTF-8" 实为 Latin-1,属上游编码笔误

### 1.3 autoconf 2.69 临时目录 umask 077 与 OHOS HMMAC 冲突

- 第三条真实错误:`./config.status[1003]: can't create ./confXXXXXX/subs1.awk: Permission denied`
- 设备实测(在 `$HOME/tmp` 下):
  - 默认 umask 0002 → mkdir 得 `drwxrws--x`,写入 OK
  - umask 022 → `drwxr-s--x`,写入 OK
  - umask 077 → `drwx--S---`(意外带 setgid 位),写入 **Permission denied**;`chmod 700` 后仍被拒
- 结论:OHOS HMMAC/HMDFS 对 0700 全私有目录拒绝写入(即使属主);autoconf 2.69 的 AS_TMPDIR(.configure 与生成的 config.status 各一份)用 `umask 077 && mktemp -d` 创建临时目录,必然触发
- 修复:补丁将 configure 内两处 `umask 077` 改为 `umask 022`(config.status 内副本随生成自动继承)
- 过程教训:曾因修改 configure.ac 触发 automake maintainer 规则,missing --run autoconf 用系统 autoconf 2.73 重建 configure 并覆盖全部补丁 → 后续 make 报 config.status umask 失败。构建顺序固定为:转码 → umask 补丁 → `touch aclocal.m4 configure [config.h.in] 各 Makefile.in` 固定时间戳 → configure → make,防止 maintainer 重建

### 1.4 conan 构建(CONFIG_SHELL=bash)下 libtool 转义损坏

- 现象:conan create 时 make 阶段 `../../libtool: line 350: syntax error near unexpected token '}'`
- 根因:OHOS profile buildenv 的 `CONFIG_SHELL=/data/service/hnp/bin/bash` 聚合在配方 env 之后必胜;在 bash 下,configure 由 ltmain.sh 2.4.2 生成 libtool 时 `archive_expsym_cmds` 的内部引号转义(`\"`)被剥除,bash 解析到版本脚本字符串处语法崩溃;同一链路在设备 `/bin/sh`(mksh)下完整成功
- 修复:build() 内以命令行前缀赋值跑 configure(`CONFIG_SHELL=/bin/sh ...`),前缀赋值优先于聚合 env;make/Makefile 的 SHELL 随 configure 检测结果变为 /bin/sh

### 1.5 profile cppstd=17 暴露 ISO C++17 动态异常规范

- 现象:`BoolExprParser.h:107: error: ISO C++17 does not allow dynamic exception specifications`
- 根因:上游 2005 年代码用 `throw(Error)`(C++17 起非法);原生探索时 clang 15 默认 gnu++14 未触发,conan toolchain 按 profile `compiler.cppstd=17` 注入 `-std=c++17` 后暴露
- 修复:补丁将 12 处 `throw(Error)` 改为语义等价的 `noexcept(false)`(BoolExprParser.h 6 处、.cpp 6 处)

### 1.6 maintainer 重建链的时间戳防御

- 现象(首两轮 conan create):configure 成功后 make 触发 aclocal/automake/autoconf(missing fallback),系统 autoconf 2.73 重新生成 configure,**完全覆盖补丁**(umask 022 丢失),config.status 回到 077 失败;build 目录出现 autom4te.cache
- 根因:补丁改写 configure/configure.ac 使其 mtime 新于 aclocal.m4;macros/*.m4(2016)又新于被 pin 的 aclocal.m4(2001)→ 重建链逐级触发
- 修复:补丁应用后把全依赖链文件(`.m4/.am/.in/.ac`、configure、config.guess/sub、ltmain.sh、compile、depcomp、missing、install-sh)统一 utime 到 2001-01-01;GNU make 视相等 mtime 为最新,重建链彻底不触发(设备实测零 autom4te.cache)

## 2. 原生验证结果(探索副本,$HOME/tmp/boolstuff-0.1.16/src-extract)

- configure exit 0;`make -j1` exit 0;产物:
  - `src/boolstuff/.libs/libboolstuff-0.1.so.0.0.0`(ELF aarch64 共享库)
  - `src/commands/booldnf`(`booldnf --version` → `booldnf 0.1.16`)
- `make install` 到独立 prefix:bin/booldnf、lib/libboolstuff-0.1.so*、include/boolstuff-0.1/boolstuff/{BoolExpr.h,BoolExpr.cpp,BoolExprParser.h,c-api.h}、pkgconfig、man3/man1

## 3. 上游测试(make check)

统计单位:用例(测试脚本中每行输入/每条断言)。TOTAL = PASS + FAIL + SKIP + NOT_RUN。

| 套件 | 单位 | TOTAL | PASS | FAIL | SKIP | NOT_RUN |
| --- | --- | --- | --- | --- | --- | --- |
| check-test-cases.pl(库 DNF,test-cases.txt) | 用例 | 52 | 52 | 0 | 0 | 0 |
| checkc(C API 断言程序) | 程序 | 1 | 1 | 0 | 0 | 0 |
| booldnf 行为断言(--version/--help/--unknown/空 stdin) | 断言 | 4 | 4 | 0 | 0 | 0 |
| test-regressions.pl(booldnf 回归) | 用例 | 60 | 60 | 0 | 0 | 0 |
| **合计** | | **117** | **117** | **0** | **0** | **0** |

- 取数命令:
  - `grep -vE '^\s*(#|$)' src/boolstuff/test-cases.txt | wc -l` → 52
  - `grep -cE '^(.*?)\s*=>\s+(.*?)$' src/commands/regressions.txt` → 60
  - 日志:`./check-test-cases.pl: Success.`、`End of ./test-regressions.pl: 0 error(s) out of 60 tests.`、make check exit 0
- 无上游默认未编译的用例组;无跳过

## 4. Conan 配方

- 无第三方依赖(requirements 为空),W0 无依赖可直接满足
- 产物:库(libboolstuff-0.1)+ booldnf 工具;非系统同名库,保留 .so
- `package_info`:`includedirs=["include/boolstuff-0.1"]`(与上游 pkgconfig Cflags 一致)、`libs=["boolstuff-0.1"]`
- 补丁:`patches/0001-ohos-autotools-compat.patch`(configure.ac/configure 的编码转换 + umask 022)、`patches/0002-cpp17-noexcept.patch`(12 处 throw(Error) → noexcept(false));两补丁在 pristine 上按序 dry-run + 实际应用验证,与探索副本逐字节一致
- build() 手动 configure(`CONFIG_SHELL=/bin/sh` 前缀赋值,绕开 profile buildenv 的 bash)+ Autotools.make + make check;补丁后 pin 全链时间戳防 maintainer 重建
- build() 内集成上游 make check(见上)

## 5. test_package(消费者验证)

| 消费者 | 断言 | 验证内容 |
| --- | --- | --- |
| test_parser.cpp(C++,链接共享库) | 运行时 23 项(check 输出实测 `23 checks, 0 failures`) | 解析、DNF 转换(期望值与上游 booldnf/test-cases.txt 实测一致)、DNFTermRoots、getTreeVariables、解析错误异常;退出码=失败数 |
| test_c_api.c(C,经 C++ 驱动链接) | 30 条 assert(运行输出 `C API consumer test: PASS`) | 手工建树/打印/DNF/克隆/term roots/变量集/解析/错误码(IdentifierExpected=3,实测)/契约语义(DNF 消费原树,只可 destroy 返回树) |
| booldnf 命令(grep 精确匹配) | 2 项 | `--version` 输出;`(a|b)&(a|c)` → `a|a&b|a&c|b&c` |

- 关键实测:c-api.h 注释称 DNF 可对 `a&!a` 返回 NULL,实测本版本返回非 NULL 且打印 `a&!a`,注释与实现不符,测试按实测语义断言
- 之前 probe 崩溃(SIGTRAP)根因是违反 API 契约:对已被 DNF 转换消费的原树调用 destroy_tree(double free,scudo abort);修正后全绿。C API 消费者须用 C++ 驱动链接(上游 force-cxx-linking.cpp 同因)

## 6. 遗留风险

- CI worker 若 PATH 无 perl,make check 的两个 perl 驱动会失败(checkdnf/checkc 编译类测试不受影响);设备实测 perl 5.44 + IPC::Open2 可用
- 上游主页(sarrazip.com)失效,conandata 使用 Debian pool 权威镜像,SHA-256 已与 dsc 交叉核对
