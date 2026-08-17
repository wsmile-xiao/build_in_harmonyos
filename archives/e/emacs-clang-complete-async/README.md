# emacs-clang-complete-async

> Emacs clang 异步代码补全后端（clang-complete 二进制）

## 简介

emacs-clang-complete-async 是一个 Emacs 扩展，用于补全 C 和 C++ 代码。它使用 libclang 实时解析源代码，并以异步客户端-服务器方式向 auto-complete 提供补全候选。

该扩展由客户端（auto-complete-clang-async.el，用 elisp 编写）和服务器端（clang-complete 二进制，用 C 编写）组成。

## OHOS 适配要点

- completion.h 缺少 `#include <stdio.h>`，导致 FILE 类型未定义
- msg_dispatcher.c 和 msg_handlers.c 使用 LINE_MAX，需定义 `_POSIX_C_SOURCE`
- 使用系统 SDK 的 llvm-config 获取 libclang 的编译/链接标志
- Makefile 的 install target 不支持 DESTDIR，需在 Conan package() 中手动安装
- 二进制需使用 binary-sign-tool 签名才能在 OHOS 上执行

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| clang/LLVM | 20.1.8 | 提供 libclang (C API) 和 llvm-config 工具 |

## 功能验证

```bash
# 编译
make

# 验证二进制可执行（需要 libclang.so 在 LD_LIBRARY_PATH 中）
./clang-complete
# 预期输出: Source file name must be specified as the last commandline argument
```

## 参考

- 上游仓库: https://github.com/Golevka/emacs-clang-complete-async
