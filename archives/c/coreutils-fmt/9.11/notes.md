# coreutils-fmt 9.11 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-08
- 编译器: Clang 15.0.4 (HarmonyOS NDK)
- C 库: musl libc
- 目标平台: aarch64-unknown-linux-ohos
- 状态: built

## 软件说明
coreutils-fmt 是从 GNU coreutils 9.11 中提取的 `fmt` 文本格式化命令。
fmt 用于将文本段落重新换行到指定宽度。

## 编译步骤
1. 下载 coreutils-9.11.tar.gz 并解压 (SHA256: 2033b8a3049c06bff49a9e3cea72bdf4683bcd0cbeb975211dd56dbaf8b736ae)
2. 应用 2 个补丁到 work 目录
3. `./configure --prefix=$TEST_PREFIX CFLAGS='-fPIC -O2 -g' CC=clang`（~12min）
4. `make -j1` 编译全部 coreutils（含 fmt）
5. 验证 `src/fmt --version` 输出 `fmt (GNU coreutils) 9.11`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 缺少 aarch64:HarmonyOS case | 补丁 0001: 添加 HarmonyOS 识别 |
| 2 | config.status 无法创建临时文件 | mktemp -d 创建的目录权限损坏 (HMDFS MAC) | mktemp wrapper 返回失败，强制 autoconf 使用 mkdir |
| 3 | gnulib freadahead.c #error | HAVE___FREADAHEAD 未定义，musl opaque FILE | 补丁 0002: 添加 __OHOS__ musl fallback |

## 与 coreutils 9.10 的差异
| 维度 | 9.10 | 9.11 |
|------|------|------|
| freadptr.c/freadseek.c | 存在，需要补丁 | 已移除，不需要补丁 |
| freadahead.c | 需要补丁 | 需要补丁（相同模式） |
| fstat EACCES 补丁 | 需要（cat/dd/head/sort/split/tail/wc/od） | 不需要（fmt 不使用 fstat/lseek） |
| config.guess | 需要补丁 | 需要补丁（相同） |

## 源码修改
| 文件 | 修改内容 | 补丁 |
|------|----------|------|
| build-aux/config.guess | HarmonyOS 系统检测 | 0001 |
| lib/freadahead.c | musl libc opaque FILE fallback | 0002 |

## 依赖版本
- Clang 15.0.4 (HarmonyOS NDK)
- musl libc（系统自带）
- LLVM 工具链（llvm-ar, llvm-ranlib, llvm-strip）
- 无第三方依赖

## 测试结果
- fmt 5 个测试文件，14 个子测试
- PASS: 14 / FAIL: 0 / SKIP: 0

## 交付物
| 文件 | 说明 |
|------|------|
| fmt (182KB) | 文本格式化命令行工具 |
---

**编译结束**: 2026-09-08 10:08
**最终状态**: built
