# clipmenu 6.2.0 适配笔记

## 编译环境
- 构建系统: 纯 shell 脚本（无编译，Makefile 仅 install 目标）
- 编译日期: 2026-09-16
- 状态: built

## 编译步骤

clipmenu 是纯 bash 脚本工具集，无需编译：
1. conan source 下载源码并应用补丁
2. conan build 无操作（pass）
3. conan package 复制 5 个脚本（clipmenu/clipmenud/clipdel/clipctl/clipfsck）到 bin/，
   上游测试套件 tests/ 打包进包目录（供 test_package 运行），LICENSE 到 licenses/

## 上游测试验证

上游测试套件 tests/test-clipmenu（bats 风格 bash 测试，13 个断言）已实际运行并通过。
关键发现：上游测试通过 bash 函数 shim 掉了 dmenu/rofi/xsel/xclip，
**不需要真实 X11 环境**，唯一的平台适配点是硬编码的 /tmp/clipmenu 路径。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tests/test-clipmenu 报 "Read-only file system" | 测试硬编码 /tmp/clipmenu，鸿蒙 /tmp 只读（E002） | 补丁 0001 引入 CM_TEST_BIN 环境变量覆盖，默认值保持上游行为 |
| 2 | test_package 找不到上游测试 | test_package 无法访问配方源码目录 | 主配方将 tests/ 打包进包目录，test_package 从包目录运行 |

## 源码修改

- patches/0001-tests-allow-override-hardcoded-tmp-path.patch：
  tests/test-clipmenu 和 tests/test-perf 中 6 处硬编码 /tmp/clipmenu 改为
  "${CM_TEST_BIN:-/tmp/clipmenu}"（无平台宏，纯 POSIX 兼容可移植性修复，符合 R8）

## 依赖版本

- xsel/1.2.1（制品仓已发布）
- clipnotify/1.0.2（制品仓已发布）

## 验证结果

```bash
conan create archives/c/clipmenu/6.2.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=default
# [install-check] clipmenu/clipmenud/clipdel/clipctl/clipfsck: OK
# Running upstream tests/test-clipmenu ...
# Upstream tests/test-clipmenu: PASS (13 assertions)
```

## 注意事项

- 测试运行需 bash（HarmonyOS 自带 mksh，CI 环境有 bash）
- test-perf 为性能基准测试，非功能性测试，不纳入验证
- 完整功能（菜单选择、剪贴板写入）仍需 X11 环境，但测试逻辑已通过 shim 全覆盖

---

**编译结束**: 2026-09-16
**最终状态**: built
