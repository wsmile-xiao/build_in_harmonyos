# spdlog 1.17.0 编译笔记

**日期**: 2026-08-27
**状态**: ✅ Conan 配方完成

## 背景

spdlog 1.11.0 已有完整的鸿蒙 PC conan 配方（fmt/8.1.1 + SPDLOG_FMT_EXTERNAL=ON）。
spdlog 1.17.0 此前有探索性编译记录（manifest + notes），但未完成 conan 适配。

## 与 1.11.0 的关键差异

### fmt 版本升级

- **1.11.0**: `self.requires("fmt/8.1.1")` — spdlog 1.11.0 的 `spdlog/fmt/fmt.h` 引用 `fmt/core.h`（fmt 8 兼容）
- **1.17.0**: `self.requires("fmt/12.2.0")` — spdlog 1.17.0 的 `spdlog/fmt/fmt.h` 引用 `fmt/base.h`（fmt 10+ 才有的头），fmt 8 不兼容
- spdlog 1.17.0 内置 bundled fmt 12.1.0，使用 fmt/12.2.0（>=12.1.0）外部构建

### 配方继承

- 完全继承 1.11.0 的 OHOS 平台适配：
  - CMAKE_SYSTEM_NAME=OHOS 守卫（避免 cmake "System is unknown" 警告导致 SONAME 缺失）
  - 二进制签名（_sign_binaries + _resolve_sign_tool）
  - include 目录检测（避免 fmt/locale.h 遮蔽 musl locale.h）
  - SPDLOG_FMT_EXTERNAL + SPDLOG_COMPILED_LIB 通过 cpp_info.defines 传给消费方

## 知识提取

| # | 发现 | 层级 | 写入位置 | 状态 |
|---|------|------|----------|------|
| 1 | spdlog 1.17.0 需 fmt 10+（fmt/base.h），使用 fmt/12.2.0 | L3 | manifest.yaml | ✅ |
| 2 | 1.11.0→1.17.0 API 无 breaking change，test_package 可复用 | L3 | notes.md | ✅ |
| 3 | OHOS 平台适配（CMAKE_SYSTEM_NAME/签名/include检测）与 1.11.0 完全一致 | L3 | conanfile.py | ✅ |
---

**编译结束

## 提交状态
- PR: 已推送至 GitCode
- W3 本地 CI 模拟: 通过
- W4 Pre-PR 审计: 通过
- PR body: 已完成**: 2026-08-27 22:13
**最终状态**: built
