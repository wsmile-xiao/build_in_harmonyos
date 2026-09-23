# libonig

当前适配版本：6.9.10

## 简介

`libonig` 是 Oniguruma 正则表达式库，支持 POSIX、Perl 风格语法以及 UTF-8、UTF-16、UTF-32 等编码。

## HarmonyOS PC 适配

- 使用上游 CMake 构建系统和 Conan `CMakeToolchain`。
- OHOS 目标根据 Conan 架构选择 `arm64-v8a` 或 `x86_64`，默认发布静态库，也支持 `shared=True`。
- Conan 包提供 `onig::onig` CMake 目标和 `oniguruma` pkg-config 模块；上游的 `onig-config` 构建辅助脚本不随纯库包发布。
- 版本级测试包含上游 7 个 CMake API 测试、Oniguruma C API 测试，以及 HarmonyOS 临时文件/API 测试。

## 使用

```c
#include <oniguruma.h>
```

链接库名为 `onig`，CMake 目标为 `onig::onig`。

## 来源

- 上游项目：https://github.com/kkos/oniguruma
- 发布版本：https://github.com/kkos/oniguruma/releases/tag/v6.9.10
- Conan 引用：`libonig/6.9.10`
