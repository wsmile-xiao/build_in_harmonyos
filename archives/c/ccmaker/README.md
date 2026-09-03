# ccmaker

Simple C library for creation and manipulation，提供基础算术与版本查询接口。

## 功能概述

- `ccmaker_add` / `ccmaker_sub` 整数运算
- `ccmaker_version` 返回版本字符串
- CMake 构建，支持静态/动态库

## OHOS 适配

- 使用 CMakeToolchain，无需补丁
- 上游 ctest 单测试在 build() 末尾执行并输出 HMBS 上游标记
- test_package 双用例验证消费者链接

## 依赖关系

- 无外部依赖

## 参考资料

- 源码: https://gitcode.com/gyccc/ccmaker
