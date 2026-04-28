# CUnit

CUnit 是一个 C 语言的单元测试框架，提供编写、管理和运行测试用例的系统。

## 功能概述

- C 语言单元测试框架
- 支持测试套件和测试用例的组织
- 多种输出界面（控制台、自动、Basic 等）
- 断言宏
- 注册和执行测试

## OHOS 适配

- autotools configure 在 HarmonyOS 上因临时文件权限问题失败
- 需要手动编译方式绕过：
  1. 手动替换 CUnit.h.in 中的 @VERSION@ 和 @RELEASE@
  2. 手动编译源文件
  3. 创建静态库 libcunit.a

## 依赖关系

- C 编译器

## 参考资料

- 官网: https://cunit.sourceforge.net/
