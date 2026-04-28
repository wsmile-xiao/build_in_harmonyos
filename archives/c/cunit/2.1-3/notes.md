# cunit 2.1-3 适配笔记

## 编译环境
- 构建系统: custom（手动编译，绕过 autotools）
- 编译日期: 2026-04-27
- 编译器: clang
- 状态: success

## 编译步骤
autotools configure 失败，采用手动编译：
1. 手动替换 CUnit.h.in 中的 @VERSION@ 和 @RELEASE@
2. 手动编译所有 C 源文件
3. 创建静态库 libcunit.a

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 创建临时文件权限错误 | HarmonyOS HMDFS 临时文件权限限制 | 手动编译绕过 autotools |
| 2 | config.sub/config.guess 不识别 HarmonyOS | 需要更新为支持 ohos 的版本 | 更新配置文件 |

## 交付物
| 文件 | 说明 |
|------|------|
| libcunit.a | 静态库 (111KB) |
| CUnit.h + 12 个头文件 | 头文件 |
| cunit-2.1-3-ohos-aarch64.tar.gz | 预编译包 |
| cunit-2.1-3-ohos-aarch64-debug.tar.gz | Debug 包 |
