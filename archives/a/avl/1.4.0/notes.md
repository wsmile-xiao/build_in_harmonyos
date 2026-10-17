# avl 1.4.0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4 (环境无 gcc/cc，configure 需显式 CC=/data/service/hnp/bin/clang)
- 状态: built

## 编译步骤

```bash
export CC=/data/service/hnp/bin/clang AR=/data/service/hnp/bin/llvm-ar RANLIB=/data/service/hnp/bin/llvm-ranlib
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: no acceptable cc found in $PATH` | 环境只有 clang，无 gcc/cc 符号链接 | configure 前设置 `CC=/data/service/hnp/bin/clang`，`AR/llvm-ar`、`RANLIB/llvm-ranlib` 一并显式指定 |
| 2 | `make: texi2html: No such file or directory` (avl.html) + makeinfo 缺失警告 | 环境无 texi2html/makeinfo (texinfo 工具链) | 非致命：文档目标由 Makefile 标记 `Error 127 (ignored)` 忽略，库静态库与头文件正常产出 |
| 3 | license 需按上游校正 | 生成模板默认 MIT | 上游 COPYING 为 GPL v2，conanfile.py license 改为 GPL-2.0 |

## 源码修改

无补丁（patches 为空）。上游源码零改动适配。

## 依赖版本

无第三方依赖（纯 C 单库，仅依赖 libc）。

## 验证结果

```bash
make check  →  All 5 tests passed (avl-test avlt-test avltr-test thread-test rb-test)
test_package 消费者测试 → create/insert/count/find/delete/destroy 断言全过 (16 断言)
```

上游官方源: https://ftp.gnu.org/gnu/avl/avl-1.4.0.tar.gz
sha256: 8f6a368bad72dac4fd2586dc7a8419d47abcbbc44f4780ef1efdedbf9c42831f
---

**编译结束**: 2026-09-07 00:13
**最终状态**: built
