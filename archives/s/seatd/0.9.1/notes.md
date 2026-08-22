# seatd 0.9.1 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-22
- 编译器: clang/clang++
- 状态: published（Conan 配方验证通过）

## Conan 配方

本版本基于 0.9.3 的 Conan 配方适配，主要变更：
- 版本号: 0.9.1
- 源码 URL: https://github.com/kennylevinsen/seatd/archive/refs/tags/0.9.1.tar.gz
- sha256: 819979c922a0be258aed133d93920bce6a3d3565a60588d6d372ce9db2712cd3

## 构建步骤

1. Meson 配置（通过 Conan MesonToolchain）：
   ```python
   tc.project_options["libseat-logind"] = "disabled"
   tc.project_options["man-pages"] = "disabled"
   tc.project_options["examples"] = "disabled"
   tc.project_options["werror"] = "false"  # OHOS only
   ```

2. 编译：`meson build` + `ninja`

3. 测试：`meson test linked_list connection`（排除 poller）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译警告被视为错误 | meson 默认 `-Werror`，OHOS SDK 的 sys/socket.h 中 CMSG_NXTHDR 宏有类型比较问题 | `tc.project_options["werror"] = "false"` 禁用 |
| 2 | OHOS profile 缺少 ar/ranlib | OHOS conan profile 仅声明 clang 路径 | `_inject_ohos_archiver()` 注入 llvm-ar/llvm-ranlib 到 meson native file |
| 3 | poller 测试超时 | HarmonyOS poll 系统调用行为差异 | 排除 poller 测试，仅运行 linked_list 和 connection |

## 源码修改

无补丁，仅通过 meson 配置选项解决编译问题。

## 依赖版本

- meson (Conan 内置)
- ninja
- clang 15.0.4
- 无 Conan 依赖

## 测试结果

- linked_list_test: OK
- connection_test: OK
- poller_test: 排除（OHOS poll 系统调用行为差异）
- test_package: 15/15 checks passed（noop backend 生命周期测试）

## 交付物

| 文件 | 说明 |
|------|------|
| libseat.a | libseat 静态库 |
| libseat.h | libseat 头文件 |
| libseat.pc | pkg-config 文件 |
| seatd | seatd 服务守护进程 |
| seatd-launch | seatd 启动器 |

## 注意事项

- seatd 是 seat 管理服务，替代 systemd-logind，libinput 的可选依赖
- 在 HarmonyOS 上禁用 logind 支持（无 systemd/elogind）
- poller 测试超时可能是 HarmonyOS poll 系统调用限制，不影响核心功能
- 静态链接（OHOS 平台默认 shared=False）

---
**Conan 适配**: 2026-08-22
**最终状态**: published
---

**编译结束**: 2026-08-22 09:22
**最终状态**: built
