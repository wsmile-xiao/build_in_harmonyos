# libzen

ZenLib - small C++ library

## 描述

ZenLib 是一个小型 C++ 库，提供了一些通用的工具类和函数。

## 补丁说明

本软件需要以下补丁以适配鸿蒙平台：

- `0001-Source-ZenLib-Thread.cpp.patch`: `Thread::ForceTerminate()` 将
  `pthread_cancel` 声明为 weak 弱符号并在调用前判空（libc 探针）。根因：
  OHOS musl 的 libpthread 无 `pthread_cancel` 符号（nm -D 与交叉链接
  探针实证）。weak 声明使有该符号的 POSIX libc 保持上游取消语义；OHOS
  等无符号 libc 上解析为 NULL、跳过调用（协作式终止经 RequestTerminate
  完成）。不引入平台条件编译宏（R8 合法例外）。
  补丁为两处最小 hunk（CRLF，与上游源行尾一致，patch_ng 与 git apply
  双验证）。

## conan 配方

- `0.4.41/conanfile.py` + `conandata.yml`（2026-09-27 补齐）
- 构建入口 `Project/CMake`（tarball 顶层无 CMakeLists）
- 无第三方依赖（仅 pthread 系统库）
- test_package：自研功能断言（上游无测试框架，Example demo 含交互
  `system("PAUSE")` 不可用，详见 0.4.41/notes.md）

## 已编译版本

- 0.4.41 (2026-09-27, conan 配方, 状态 built)