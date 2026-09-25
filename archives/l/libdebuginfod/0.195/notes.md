# libdebuginfod 0.195 — 移植笔记

## 任务
- contrib 13121,分支 feat/libdebuginfod-0.195,认领 2026-09-24
- 上游:elfutils 0.195 tarball(debuginfod 子树),同源 elfutils/0.195 配方

## 交付物
- lib/libdebuginfod.so{,.1} + libdebuginfod.a(客户端库)
- bin/debuginfod-find(客户端查询工具)+ bin/debuginfod(服务端,测试套件依赖)
- include/debuginfod.h

## 同源说明
elfutils/0.195 配方显式 `--enable-libdebuginfod=dummy --disable-debuginfod`
(交付里无 debuginfod 组件)。本包交付该组件的真实实现
(--enable-libdebuginfod=libcurl --enable-debuginfod),先例:gtest_main 之于 gtest。

## 配方机制(相对 elfutils/0.195 模板的增量)
- requires 增加:curl/8.15.0(客户端)、json-c/0.17 + libmicrohttpd/1.0.1 +
  sqlite3/3.49.1 + libarchive/3.8.7(服务端,configure.ac:944 判定串要求
  have_jsonc+HAVE_CXX11+libarchive+sqlite3 全 yes)、elfutils/0.195
  (客户端库链接 libelf 的 elf_version/elf_begin 等,运行时由 elfutils 包提供)
- tool_requires 增加:pkgconf/3.0.6(PKG_CHECK_MODULES 探测需要)
- generate():PkgConfigDeps + PKG_CONFIG_PATH 指向 generators 目录
- generate():musl error.h shim(注入 -I,仅构建期)——上游测试程序大量
  调用 error()/error_at_line(),musl 无此头
- 补丁 0001/0002 与 elfutils 配方同源;0003(2 个测试文件死 include error.h)、
  0004(tests/Makefile.in 剔除 5 个 pthread_cancel 测试程序)为测试基建适配

## 上游测试真机执行(2026-09-24)
- automake harness:make check(tests/),TOTAL=292,PASS=211,SKIP=43,FAIL=38(72.3%)
- 运行前提:LD_LIBRARY_PATH 含全部 conan 依赖库目录(test-subr.sh 只带构建树内库)
- SKIP 43:debuginfod-*(上游 exit 77:perl/rpm2cpio/cpio/ss/bsdtar 不可得)、
  eu-search-*(pthread_cancel 剔除)、biarch/core 特化
- FAIL 38 分类:
  1. 测试基建差异(toybox wc 无 GNU --lines 长选项):run-strip-* 系列 ~18
  2. OHOS ELF 平台特性(elflint 对 .note.ohos.ident/GNU_RELRO/.gnu.version
     布局报警):run-elflint-self、run-readelf-self 等
  3. 平台安全模型(ptrace//proc 受限):run-backtrace-native、run-stack-*、
     dwfl-bug-fd-leak、vdsosyms、run-deleted
  4. 压缩率断言(zlib 版本差异):run-compress-test

## 消费者测试
- test_debuginfod.c:客户端 API 全链路(rc=-111 = ECONNREFUSED,文档语义)
- test_debuginfod_cli.sh:debuginfod-find --version + 不可达查询非零退出
