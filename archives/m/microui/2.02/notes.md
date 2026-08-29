# microui 2.02 适配笔记

## 编译环境
- 构建系统: 纯 ANSI C 源码（Conan makefile recipe）
- 上游提交: `0850aba860959c3e75fb3e97120ca92957f9d057`
- 编译器: clang
- 目标平台: OpenHarmony armv8

## 编译步骤

Conan 配方直接使用 `clang -fPIC -O2 -I src -c src/microui.c` 编译核心实现，并使用 `llvm-ar` 生成 `libmicroui.a`。上游没有 configure、Makefile 或正式测试目标。

## 源码修改

无源码补丁。源码保持上游提交内容不变。

## 依赖版本

无第三方依赖。

## 测试

上游仓库仅提供 demo，没有独立测试套件。`test_package/test.c` 作为适配补充测试，调用 `mu_init`、`mu_begin_window`、`mu_layout_row`、`mu_label` 和 `mu_next_command` 验证消费者链接与核心命令生成。

## 验证结果

```text
conan-verify microui 2.02: PASS
W3 本地 CI: PASS
消费者集成测试: 1/1 (100%)
```
---

**编译结束**: 2026-08-28 17:49
**最终状态**: built
