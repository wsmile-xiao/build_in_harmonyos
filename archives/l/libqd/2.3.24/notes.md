# libqd 2.3.24 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤
GitHub tag 无 configure；autoreconf 后 `--host/--build=aarch64-unknown-linux-musl --disable-fortran`。真机 `conan create` CREATE_EXIT:0；`make check` PASS qd_test/pslq_test/c_test；test_package `libqd version=2.3.24 ... ok`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识 HarmonyOS | E007 | `--build/--host=aarch64-unknown-linux-musl` |
| 2 | config.status subs1.awk Permission denied | HMDFS + mktemp -d 0700 | 改 mkdir + umask 000 |
| 3 | make 编 docs/qd.pdf 要 latex | BUILT_SOURCES/dist_doc_DATA | 从 Makefile.am 去掉 |

## 依赖版本
无
