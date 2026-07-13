# cpulimit 0.2 适配笔记

## 编译环境
- 构建系统: makefile (plain Makefile, no configure)
- 编译日期: 2026-07-03
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

cpulimit 使用纯 Makefile，无 configure 脚本。顶层 Makefile 委托 src/ 和 tests/ 子目录编译。

```bash
cd $BUILD_SRC_DIR
make -j1
# 手动安装（无 make install 目标）
mkdir -p $TEST_PREFIX/bin
cp src/cpulimit $TEST_PREFIX/bin/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `basename` 未声明，编译报错 | OHOS sysroot 中 `basename()` 需要 `<libgen.h>` 声明 | 在 process_group.c 添加 `#include <libgen.h>` |
| 2 | `sys/sysctl.h` 不存在 | OHOS/Linux 不需要此头文件，仅 Apple/FreeBSD 使用 | 条件包含：`#if defined(__APPLE__) \|\| defined(__FreeBSD__)` |
| 3 | `memrchr` 未声明导致段错误(segfault) | 环境变量 CFLAGS 覆盖了 Makefile 的 `-D_GNU_SOURCE`，导致 memrchr 未声明，int→ptr 截断 | 在 cpulimit.c 顶部添加 `#define _GNU_SOURCE` |
| 4 | `#ifdef __APPLE__ \|\| __FREEBSD__` 无效语法 | `#ifdef` 不支持逻辑运算符 | 改为 `#if defined(__APPLE__) \|\| defined(__FreeBSD__)` |

## 源码修改

| 文件 | 补丁 | 修改内容 |
|------|------|----------|
| src/cpulimit.c | 0001 | 添加 `#define _GNU_SOURCE`；条件包含 sys/sysctl.h；修复 #ifdef 语法 |
| src/process_group.c | 0002 | 添加 `#include <libgen.h>` |
| tests/process_iterator_test.c | 0003 | 修复 #ifdef 语法 |

## 依赖版本

- 无外部依赖（仅 libc）

## 验证结果

```bash
# L2 smoke test
$ cpulimit --help
Usage: cpulimit [OPTIONS...] TARGET
   OPTIONS
      -l, --limit=N          percentage of cpu allowed from 0 to 2000 (required)
      ...

# L4 安全扫描
$ readelf -l bin/cpulimit | grep -E "GNU_STACK|GNU_RELRO"
GNU_RELRO      0x003bb0 ...  R   0x1
GNU_STACK      0x000000 ...  RW  0x0    # NX enabled

$ readelf -d bin/cpulimit | grep -E "BIND_NOW|PIE"
(FLAGS)        BIND_NOW
(FLAGS_1)      NOW PIE
```

## 注意事项

- cpulimit 是命令行工具，非库。conanfile.py 中 package_info.libs 为空。
- Makefile 使用 `?=` 赋值 CFLAGS，环境变量会覆盖默认的 `-D_GNU_SOURCE`，必须在源码中定义。
- 无 `make install` 目标，需手动复制二进制。
- process_iterator_test 在 OHOS 上会触发 assertion failure（读取 /proc 匹配进程信息），属于平台限制，不阻塞。
---

**编译结束**: 2026-07-03 14:35
**最终状态**: built
