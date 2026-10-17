# libgfshare

## 简介
Implementation of Shamir Secret Sharing in GF(2^8). Provides a small C
library (`libgfshare`) and two command-line tools (`gfsplit` / `gfcombine`)
for splitting a secret into N shares and recombining any threshold T of them
to recover the original.

## OHOS 适配
- autotools：2.0.0 tag 无 release tarball，官方源为 GitHub git-archive 快照，
  仅含 configure.ac / Makefile.am（无 configure / config.sub / Makefile.in），
  build() 中 `autoreconf -fi` 从源码引导生成。
- tool_requires automake/1.18 + libtool/2.5.4 提供 aclocal/libtoolize
  （本机 automake 的 aclocal 指向不存在的 Automake/Config.pm，不可用）。
- --build/--host 显式传 aarch64-unknown-linux-ohos 跳过 config.guess 探测
  （uname -s = "HarmonyOS" 不被旧 config.guess 识别；automake 1.18 的
  config.sub 认 *-linux-ohos）。build==host 为原生构建。
- gfshare_maketable 为 noinst_PROGRAMS 构建辅助程序，make 时生成
  libgfshare_tables.h；原生构建下用 OHOS clang 编译并直接运行，无需
  build/host 分离。
- E114：生成 configure 的 config.status 用 umask 077 建临时目录，HMDFS 上
  产生不可写 setgid 目录 → 运行时删除 umask 077。
- E074：make 全部 -j1（HMDFS 禁止 jobserver fifo）。
- libtool .la 在 package() 中删除（仓库惯例）。
- gfsplit / gfcombine CLI 工具随包发布到 bin/（commands.json 已声明，R38）。

## 依赖
- 无 conan 依赖（纯 C，仅 libc）
- 编译工具: clang, autotools (tool_requires)

## 参考
- 官网: https://github.com/kinnison/libgfshare
