# aa3d 1.0 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure 脚本，无测试套件）
- 编译日期: 2026-08-04
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos，来自 /data/service/hnp/bin)
- 状态: published

## 编译步骤

aa3d 为 1998 年发布的单文件 C 程序（aa3d.c），Makefile 仅含隐含规则 `aa3d: aa3d.c`，无 configure。

1. 直接使用 make 隐式规则编译，指定 CC 为 OHOS clang：
   ```bash
   make CC=/data/service/hnp/bin/clang -j1
   ```
   产物：`aa3d`（ELF 64-bit LSB arm64，动态链接 ld-musl-aarch64.so.1，PIE）
2. 验证功能：
   ```bash
   ./aa3d < pyramid | head   # 输出正确 ASCII 立体图
   ```
3. Staging 隔离安装：
   ```bash
   mkdir -p $TEST_PREFIX/bin && cp aa3d $TEST_PREFIX/bin/
   ```
   （本平台无 `install` 命令，用 cp + chmod 替代）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译告警 `call to undeclared library function 'strcmp'/'strlen'` | 源码为 1998 年 C89 时代代码，未 `#include <string.h>` | 不影响编译与运行（libc 提供符号），未改源码，记录待后续补丁 |
| 2 | `make check` 失败：`No rule to make target 'check'` | Makefile 无测试目标 | 记录为平台事实，跳过测试 |
| 3 | `install` 命令不可用 | OHOS 精简环境无 coreutils install | 用 `cp` + `chmod` 代替 |

## 依赖版本

无第三方依赖（仅 C 标准库）。

## 验证结果

```bash
$ file aa3d
aa3d: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ ./aa3d < pyramid | head -3
WHDUC[]MUT``WHDUC[]MUT``...   # 输出正确的 ASCII 立体图

$ ./aa3d -h
Usage: ./aa3d [options] < file   # 用法/帮助正常输出
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/aa3d | ASCII art 立体图生成器可执行文件（约 22KB） |

## 注意事项

- aa3d 无 `--version` 选项；传入未知选项会打印用法说明并返回 1（可作 smoke test）。
- 典型用法：`aa3d -w 120 -d < depth.txt > output.txt`。
- 源码 URL 来自 AA-Project SourceForge 官方发布页。
---

**编译结束**: 2026-08-04 17:25
**最终状态**: published
