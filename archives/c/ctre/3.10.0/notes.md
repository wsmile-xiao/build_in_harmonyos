# ctre 3.10.0 适配笔记

> 库类型：header-only（无需编译，仅安装头文件）。Apache-2.0-with-LLVM-exception。

## 官方来源核验（Bootstrap，2026-08-30）

- 官方仓库: https://github.com/hanickadot/compile-time-regular-expressions
- 正式标签: `v3.10.0`
- 标签 commit: `e34c26ba149b9fd9c34aa0f678e39739641a0d1e`（GitHub API `git/refs/tags/v3.10.0` = commit 类型）
- 官方 release: `v3.10.0`（GitHub Releases 存在）
- 源码 tarball SHA-256:
  - codeload（canonical, 顶层目录 `compile-time-regular-expressions-3.10.0/`）: `b17e6c9a6cc0cea65132f62a6c699cefed952721063569d6339eb3ca471045e6`
  - API tarball（顶层目录 `hanickadot-compile-time-regular-expressions-e34c26b/`）: `ff6ee362e6d8faf0f0baf4fca6199afdc9b7b74377876bb675ff4bd106fffbad`
  - 两包内容 `diff -rq` 完全一致，仅顶层目录名不同。
- conandata.yml 采用 codeload canonical URL + `b17e6c9a...`。

## 结构

- header-only：`include/ctre.hpp`、`include/ctre-unicode.hpp`、`include/ctll.hpp`、`include/unicode-db.hpp` 及 `include/ctre/*.hpp`、`include/ctll/*.hpp`、`include/unicode-db/*.hpp`
- CMake：INTERFACE 目标 `ctre` / `ctre::ctre`，`CTRE_CXX_STANDARD` 默认 20
- 上游自带 `.conan/`（Travis 时代的 ConanMultiPackager，不可直接用于 Conan 2.x，需重写配方）

## 状态

- R02 Bootstrap 完成（worktree feat/ctre-3.10.0 从 main 7bc8f354 创建）
---

**编译结束**: 2026-08-30 20:49
**最终状态**: built
