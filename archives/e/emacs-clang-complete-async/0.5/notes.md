# emacs-clang-complete-async 0.5 适配笔记

## 编译环境
- 构建系统: makefile (custom Makefile + makefile.mk, uses llvm-config)
- 编译日期: 2026-08-14
- 编译器: clang 15.0.4 (system SDK)
- 状态: built

## 编译步骤

1. 下载源码: `https://github.com/Golevka/emacs-clang-complete-async/archive/refs/tags/v0.5.tar.gz`
   - waterlan.home.xs4all.nl 已失效，改用 GitHub 官方仓库 Golevka/emacs-clang-complete-async
   - GitHub tag 名为 `v0.5`（不是 `0.5`），URL 需用 `refs/tags/v0.5`
2. 源码修复（3 个文件，详见下方"源码修改"）
3. 编译: `make` (使用系统 llvm-config 获取 libclang 的 cflags/ldflags)
4. 安装到 staging: `cp -f clang-complete $TEST_PREFIX/$DEFAULT_PREFIX/bin/`
5. 签名: `binary-sign-tool sign -inFile clang-complete -outFile clang-complete -selfSign 1`
6. 验证: `LD_LIBRARY_PATH=<sdk-lib> ./clang-complete` → 正确输出 "Source file name must be specified..."

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | waterlan 站点下载返回 HTML | waterlan.home.xs4all.nl 已失效 | 改用 GitHub 官方源 Golevka/emacs-clang-complete-async，tag 为 v0.5 |
| 2 | completion.h: error: unknown type name 'FILE' | completion.h 使用 FILE* 但未 #include <stdio.h> | 在 completion.h 中添加 #include <stdio.h> |
| 3 | msg_dispatcher.c: error: use of undeclared identifier 'LINE_MAX' | musl libc 默认不暴露 LINE_MAX，需要 _POSIX_C_SOURCE | 在 msg_dispatcher.c 和 msg_handlers.c 开头添加 #define _POSIX_C_SOURCE 200809L |
| 4 | make install DESTDIR 失败 (cp /usr/local/bin) | Makefile install target 直接 cp 到绝对路径，不支持 DESTDIR | 手动 cp 到 staging 目录 |
| 5 | 运行时 libclang.so 找不到 | 二进制链接 libclang.so 但 RPATH 未设 | 运行时通过 LD_LIBRARY_PATH 或 Conan 管理依赖链 |

## 源码修改

### src/completion.h
- 添加 `#include <stdio.h>` (修复 FILE 类型未定义)

### src/msg_dispatcher.c
- 添加 `#define _POSIX_C_SOURCE 200809L` (修复 LINE_MAX 未定义)

### src/msg_handlers.c
- 添加 `#define _POSIX_C_SOURCE 200809L` (修复 LINE_MAX 未定义)

## 依赖版本

- clang/LLVM 15.0.4 (system SDK at /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm)
- libclang.so (system SDK, 链接时通过 llvm-config --ldflags 获取 -L 路径)
- Conan 依赖: 无 (libclang/llvm-config 由系统 SDK 提供，不是 Conan 包)
- 制品仓 clang/20.1.8 和 clang/22.1.8 的 binary 均损坏 (corrupted)，不可用作 Conan 依赖

## 验证结果

```bash
$ file clang-complete
clang-complete: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ LD_LIBRARY_PATH=<sdk-lib> ./clang-complete
Source file name must be specified as the last commandline argument

$ readelf -d clang-complete | grep -E "BIND_NOW|PIE"
FLAGS             BIND_NOW
FLAGS_1           NOW PIE

$ readelf -l clang-complete | grep GNU_STACK
GNU_STACK      0x0000000000000000 ... (NX enabled)
```

安全特性: NX ✓, PIE ✓, RELRO+BIND_NOW ✓

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| clang-complete | 31232 bytes | clang 异步代码补全后端二进制 |

## 注意事项

- 本软件是 Emacs 的 clang 异步代码补全后端，构建产物为可执行文件（非库）
- 运行时需要 libclang.so 在 LD_LIBRARY_PATH 或系统库路径中
- Makefile 的 install target 不支持 DESTDIR，需要 conanfile.py 的 build() 手动处理
- 构建依赖 llvm-config 工具（在系统 SDK 中提供）
- 构建产物包含可执行文件，需要 commands.json (R38)
---

**编译结束**: 2026-08-14 14:06
**最终状态**: built
