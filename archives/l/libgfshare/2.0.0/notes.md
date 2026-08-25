# libgfshare 2.0.0 适配笔记

## 编译环境
- 构建系统: autotools (GNU Autotools: autoconf 2.72 / automake 1.18 / libtool 2.5.4)
- 编译日期: 2026-08-25
- 编译器: clang (OHOS aarch64)
- 状态: built

## 编译步骤

1. 下载官方 GitHub git-archive tarball (tag 2.0.0)，SHA256 校验通过。
2. `autoreconf -fi` 从 configure.ac / Makefile.am 生成 configure、config.sub、
   config.guess、Makefile.in、aclocal.m4、ltmain.sh。
3. `_drop_umask_077()` 删除生成 configure 中的 `umask 077`（E114 HMDFS）。
4. `./configure --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos
   --enable-static --disable-shared --prefix=...`
5. `make -j1`（E074：HMDFS 禁止 jobserver fifo）。
   - make 自动编译 gfshare_maketable（noinst_PROGRAMS）并运行生成
     libgfshare_tables.h，再编译 libgfshare.la、gfsplit、gfcombine。
6. `make check -j1` 运行上游测试套件（L1）。
7. `make install` 安装 lib/libgfshare.*、include/libgfshare.h、
   lib/pkgconfig/libgfshare.pc、bin/gfsplit、bin/gfcombine、man pages。
8. package() 删除 libtool .la 包装文件。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | git-archive 无 configure 脚本 | 2.0.0 tag 无 release dist tarball，仅源码快照 | build() 中 `autoreconf -fi` 从 configure.ac 生成 |
| 2 | 本机 automake aclocal 不可用 | aclocal 指向 automake-1.17 但仅 1.16 的 Config.pm 存在 | tool_requires automake/1.18 + libtool/2.5.4 |
| 3 | config.guess 不识别 HarmonyOS | uname -s = "HarmonyOS" | --build/--host 显式传 aarch64-unknown-linux-ohos 跳过探测 |
| 4 | config.status 建临时目录失败 | E114: HMDFS 上 umask 077 建的 0700 目录不可写 | `_drop_umask_077()` 运行时删除 umask 077 |
| 5 | make -j>1 卡住/报错 | E074: HMDFS SELinux 禁止 jobserver fifo | 全部 make 调用带 -j1 |
| 6 | gfshare_maketable 交叉编译问题 | noinst_PROGRAMS 构建辅助程序需在构建机运行 | build==host 原生构建，直接用 OHOS clang 编译运行，无需 build/host 分离 |

## 源码修改

无补丁。源码树未做任何修改；所有适配在 conanfile.py 运行时完成
（autoreconf 引导 + umask 077 删除 + triplet 显式传入）。

## 依赖版本

- 无 conan 依赖（纯 C，仅 libc）
- tool_requires: automake/1.18, libtool/2.5.4

## 验证结果

上游测试 (make check):
- test source files: 3 (2 C + 1 shell)
- check_PROGRAMS: 2
- TESTS: 3
- compile: 2/2 C 测试编译通过
- runtime: 3/3 通过（2 C 测试 + 1 shell 集成测试）

consumer test:
- programs: 1 (test_libgfshare)
- CHECK calls: 6
- PASS: 6/6

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libgfshare.a | 静态库 |
| include/libgfshare.h | 公开头文件 |
| lib/pkgconfig/libgfshare.pc | pkg-config 文件 |
| bin/gfsplit | secret 分割 CLI 工具 |
| bin/gfcombine | secret 恢复 CLI 工具 |
| man/man1/gfsplit.1, gfcombine.1 | 手册页 |
| man/man5/libgfshare.5 | 手册页 |
| man/man7/gfshare.7 | 手册页 |

## 注意事项

- gfshare_maketable 是构建阶段生成器（noinst_PROGRAMS），生成
  libgfshare_tables.h 后不随包发布。本包为原生 OHOS arm64 构建
  (build==host)，maketable 用目标 clang 编译并直接运行，无需 Conan
  build/host 分离。如未来改为真正交叉编译（build≠host），需将
  gfshare_maketable 拆为 build 工具单独编译。
- gfsplit/gfcombine 随包发布到 bin/，commands.json 已在软件级目录声明 (R38)。
