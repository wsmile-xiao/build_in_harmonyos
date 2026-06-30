# parallel 20260522 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-13
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `ohc-run.py init-build parallel 20260522 --url=https://ftp.gnu.org/gnu/parallel/parallel-20260522.tar.bz2`
2. `cd $BUILD_SRC_DIR && ./configure --prefix=$DEFAULT_PREFIX`
3. `make -j2 && make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SHELL=/bin/bash 导致构建失败 | HarmonyOS musl 环境下 /bin/bash 不存在，需使用 @SHELL@ | 修改 Makefile.in 将 SHELL=/bin/bash 改为 SHELL=@SHELL@ |

## 源码修改

- `Makefile.in`: 将 `SHELL = /bin/bash` 改为 `SHELL = @SHELL@`（让 autotools 自动检测系统 shell）

## 验证结果

```bash
parallel --version
GNU parallel 20260522
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| parallel-20260522-ohos-aarch64.tar.gz | ~2MB | Release包 |
| parallel-20260522-ohos-aarch64-debug.tar.gz | ~2MB | Debug包 |

## 注意事项

- GNU parallel 是 shell 工具，Makefile.in 中硬编码 /bin/bash 需改为 @SHELL@
---
**编译结束**: 2026-06-13 20:35
**最终状态**: built
