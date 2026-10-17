# fastfec 0.2.0 适配笔记

## 编译环境
- 构建系统: custom (zig→clang, 纯 C 源码)
- 编译日期: 2026-08-31
- 编译器: clang 15.0.4
- 状态: published

## 适配选型决策
- 上游构建系统为 Zig (build.zig)。尝试路径 A (tool_requires zig/0.15.2) 失败：zig 0.15.2 的 Build API 有 breaking change (ExecutableOptions 无 target 字段)，build.zig 是为旧版 zig 写的，需大量改写。
- 选用路径 B：源码为纯 C，文件清单已知，直接用 clang 逐文件编译。PCRE vendored 一起编。

## 编译步骤
```bash
CC=clang
CFLAGS="-std=gnu99 -pedantic -Wall -W -Wno-missing-field-initializers -fPIC"
PCRE_CFLAGS="-DHAVE_CONFIG_H -Isrc/pcre"

# 编译 lib 源码 (6 文件)
clang $CFLAGS -c src/buffer.c src/memory.c src/encoding.c src/csv.c src/writer.c src/fec.c

# 编译 PCRE vendored 源码 (21 文件)
clang $CFLAGS $PCRE_CFLAGS -c src/pcre/pcre_*.c

# 静态库
ar rcs libfastfec.a *.o

# 共享库
clang -shared -o libfastfec.so *.o -lm

# CLI 可执行
clang $CFLAGS -c src/cli.c src/main.c
clang -o fastfec cli.o main.o -L. -lfastfec -lm
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fastfec --help` / 无参数运行时 Signal 11 (SIGSEGV) | `newCliContext()` 中未初始化指针成员 (outputDirectory/fecId/fecName/fecUrl/fecBackupUrl/filingIdOnly/extractNumber)，当 parseArgs 在初始化这些字段前提前返回时，freeCliContext 对野指针调用 free/pcre_free 导致 crash | 在 newCliContext() 中将所有指针成员初始化为 NULL |

## 源码修改
- src/cli.c: `newCliContext()` 中补 NULL 初始化 (name/outputDirectory/fecId/fecName/fecUrl/fecBackupUrl/filingIdOnly/extractNumber)

## 依赖版本
- 无外部依赖 (PCRE vendored in src/pcre/)
- zig/0.15.2 (尝试路径A时下载验证，未使用于最终构建)

## 验证结果

### 上游测试用例（build.zig 定义 4 个 test 可执行，实际编译并运行）

上游 build.zig 第 143 行声明 `tests = [_][]const u8{ "src/buffer_test.c", "src/csv_test.c", "src/writer_test.c", "src/cli_test.c" }`，每个 test 可执行链接 lib 源码（buffer/memory/encoding/csv/writer/cli.c）+ vendored PCRE。

实际编译并运行（clang 15.0.4，2026-08-31）真实输出：

```
===== buffer_test =====

Buffer tests
ALL TESTS PASSED
Tests run: 6
[exit=0]

===== csv_test =====

CSV tests
ALL TESTS PASSED
Tests run: 3
[exit=0]

===== writer_test =====

Writer tests
ALL TESTS PASSED
Tests run: 4

[exit=0]

===== cli_test =====
CLI tests
ALL TESTS PASSED
Tests run: 8
[exit=0]
```

合计 4 个测试可执行，21 个测试用例，全部 PASS（exit=0）。未修改任何测试源码。

### CLI 工具功能验证
```bash
$ fastfec --help        # exit 1, prints usage (no crash)
$ fastfec               # exit 1, prints usage (no crash)
$ fastfec -p 123        # exit 0, prints FEC URLs
```

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| bin/fastfec | ~460KB | CLI 可执行 (解析 FEC filing→CSV) |
| lib/libfastfec.a | ~750KB | 静态库 |
| lib/libfastfec.so | ~530KB | 共享库 |
| include/*.h | - | 公共头文件 |

## 注意事项
- 上游 build.zig 的 buildOptions 含 -std=c11 和 -std=gnu99 冲突，后者生效，适配时用 -std=gnu99
- PCRE 编译需 -DHAVE_CONFIG_H
- 修复补丁在 patches/0001-init-pointers-in-newCliContext.patch
---

**编译结束**: 2026-08-31 09:19
**最终状态**: published
