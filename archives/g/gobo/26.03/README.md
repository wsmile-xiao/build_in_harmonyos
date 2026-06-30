# Gobo Eiffel 26.03 — OpenHarmony aarch64 编译归档

## 概述

Gobo Eiffel 是一个 Eiffel 编译器和工具套件，包含：

| 工具 | 说明 |
|------|------|
| gec | Gobo Eiffel Compiler（主编译器） |
| gecc | Gobo Eiffel C Compiler |
| geant | Gobo Eiffel Ant（构建工具，类似 make/ant） |
| gedoc | Gobo Eiffel Documentation |
| getest | Gobo Eiffel Test |
| gelint | Gobo Eiffel Lint |
| gecop | Gobo Eiffel Cop |
| gelsp | Gobo Eiffel Language Server Protocol |
| geimage | Gobo Eiffel Image |
| gelex | Gobo Eiffel Lex（词法分析器生成器） |
| geyacc | Gobo Eiffel Yacc（语法分析器生成器） |
| gepp | Gobo Eiffel Preprocessor |
| gexslt | Gobo Eiffel XSLT |

## 构建信息

- **版本**: 26.03
- **平台**: HarmonyOS aarch64
- **构建系统**: custom（Eiffel Bootstrap）
- **编译器**: clang-15 (LLVM 15.0.4)
- **状态**: published
- **构建日期**: 2026-06-26

## 打包产物

- **文件**: `packaging/gobo-26.03-ohos-aarch64.tar.gz`
- **大小**: 54.4MB
- **sha256**: `5595499164772a74d9ce2b0d9fc29ab27ebc575b0b1ea384c57f20e3526a910c`
- **内容**: 13 个 ELF 可执行文件（未 strip）

## 动态依赖

所有工具仅依赖 `libc.so`（系统库），无非系统动态依赖。

## 构建方式

Gobo Eiffel 使用 Bootstrap 机制编译：
1. 用 clang 编译预生成 C 源码（gec_1.c ~ gec_9.c）→ 创建 gec0
2. 用 gec0 编译 gec Eiffel 源码 → 创建 gec1
3. 用 gec1 重新编译 gec Eiffel 源码 → 创建最终 gec
4. 用 gec 编译 12 个其他 Eiffel 工具

## 平台适配

### 补丁
- `0001-tool-gec-backend-c-config-clang.cfg.patch`: 在 clang.cfg 的 libs_gc 中添加 pthread stubs

### 运行时修改
- `bootstrap.sh`: `STRIP=strip` → `STRIP=echo`（strip 会破坏 HarmonyOS ELF 执行权限）
- `pthread_stubs.c`: 新建文件，提供 `pthread_setcancelstate` 和 `pthread_cancel` 的 stub 实现

## Conan 配方

- **引用**: `gobo/26.03@ohpcd/stable`
- **conanfile.py**: 自定义构建方法（非 autotools）
- **test_package/**: 验证 6 个核心工具的 --version 输出
- **验证状态**: conan-verify 全部 8 道门禁通过

## 许可证

MIT
