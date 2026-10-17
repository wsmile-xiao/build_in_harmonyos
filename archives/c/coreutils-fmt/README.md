# GNU coreutils fmt

`fmt` — simple text formatter from GNU coreutils, packaged as a standalone Conan package.

## 功能概述

Reformat each paragraph in the FILE(s), writing to standard output.

## OHOS 适配

### 核心问题
1. **config.guess**: 不识别 HarmonyOS，需补丁添加 `aarch64:HarmonyOS` case
2. **gnulib freadahead.c**: musl libc opaque FILE 结构导致 `#error`，需 fallback
3. **mktemp HMDFS**: HarmonyOS mktemp -d 创建的目录权限损坏，需 wrapper

### 与 coreutils 9.10 的差异
- 9.11 移除了 `freadptr.c` 和 `freadseek.c`，只需修复 `freadahead.c`
- `fmt` 不使用 `fstat()`/`lseek()`，不需要 9.10 的 EACCES 补丁

## 依赖关系
- Clang 编译器（HarmonyOS NDK）
- musl libc（系统自带）
- 无额外依赖
