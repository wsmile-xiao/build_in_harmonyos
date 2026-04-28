# Check

Check 是一个 C 语言的单元测试框架，支持多种测试模式和自动检测内存泄漏。

## 功能概述

- 提供 C 单元测试框架
- 支持 Suite/TC/TCase 多层测试组织
- 自动检测内存泄漏
- 支持 fork 模式隔离测试
- 输出 XML/HTML/TAP 格式测试报告

## OHOS 适配

- 构建系统为 autotools，需要 2 个补丁（config.guess + config.sub）
- 用于其他 C 项目的单元测试

## 依赖关系

- C 编译器
- autotools 构建工具链

## 参考资料

- 官网: https://libcheck.github.io/check/
- 源码: https://github.com/libcheck/check
