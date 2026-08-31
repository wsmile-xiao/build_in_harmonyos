# CTRE (Compile Time Regular Expressions)

## 一句话

CTRE 是 C++17/20 的编译期正则表达式模板库，正则模式作为模板参数在编译期解析与编译，运行时匹配/搜索/捕获零解析开销。

## 功能概述

- 编译期正则解析：模式作为模板实参（`ctre::match<"pattern">`）
- 支持编译期与运行时匹配、搜索、捕获、子匹配、命名捕获、Unicode 属性
- 提供 `ctre::match`、`ctre::search`、`ctre::starts_with`、`ctre::split` 等接口
- header-only，无二进制产物

## OHOS 适配

- header-only 模板库，无平台相关代码，无外部依赖，OHOS aarch64 只需 C++17 编译器即可消费
- Conan 配方以 INTERFACE/header-only 方式打包 install include/ 头文件

## 依赖关系

- 编译依赖：无（纯模板 + 标准库）
- 运行依赖：无

## 参考资料

- 官网: https://compile-time.re
- 源码仓库: https://github.com/hanickadot/compile-time-regular-expressions