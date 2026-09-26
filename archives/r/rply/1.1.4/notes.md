# rply 1.1.4 适配笔记

## 编译环境
- 构建系统: 上游无构建系统（配方直接编译 `rply.c`）
- 编译日期: 2026-09-23
- 编译器: clang 15（OHOS SDK 26.0.0.18）
- 状态: built

## 编译步骤

1. 从官方 codeload 取 tag `v1.1.4` 的源码包（`rply-1.1.4.tar.gz`）。
2. `clang -O2 -fPIC -Wall -c rply.c -o rply.o` → `llvm-ar rcs librply.a rply.o`。
3. `package()` 安装 `include/rply.h`、`include/rplyfile.h`、`lib/librply.a`、`licenses/LICENSE`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无 Makefile | 项目只发布源码与 HTML 手册（Debian 自行提供构建脚本） | 配方内直接编译单个 `rply.c` 为静态库，不引入外部构建系统 |
| 2 | 无需第三方依赖 | `rply.c` 只包含 C 标准库头，不使用 libm | 无 |

## 依赖版本

无三方依赖。

## 验证结果

```bash
# 上游测试：无（N=0）
# 消费者（test_package/test_rply.c）：写一个 ASCII PLY 再读回校验
RPLY_CHECK_SUMMARY checks=18 fails=0
```

## 注意事项

- 产物为静态库 `librply.a` + 两个公共头；属于库，按 L0k 不放软件级 `commands.json`。
