# check 0.15.2 — Conan 配方

## 适配概述

Check 是一个 C 语言的单元测试框架。参考构建已使用 CMake 而非 autotools 完成。

## 构建系统

- CMake（autotools 在 OHOS 上 config.status 有兼容性问题）

## 配置选项

- `-DCMAKE_BUILD_TYPE=Release`

## 补丁

无。CMake 构建无需 config.guess/config.sub 补丁。

## 产物

- libcheck.a（静态库）
- libcheck.so（动态库）
- bin/checkmk（测试代码生成工具）
- include/check.h, check_stdint.h

## 依赖

- libm, librt（POSIX 标准，无外部依赖）

## 注意事项

- 上游测试套件需要创建临时文件，在 OHOS /tmp 只读环境下会失败
- 不影响库本身的正常使用
