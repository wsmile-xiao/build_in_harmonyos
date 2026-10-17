# bshoshany-thread-pool 5.0.0 — Bootstrap 笔记（pc3-32）

## 来源核验（bootstrap 阶段，官方资料确认）
- 官方仓库：https://github.com/bshoshany/thread-pool
- 正式标签：`v5.0.0` → commit `aa3fbfbe80762fe3ac90e2bf05e153b92536277a`（git ls-remote --tags 实测）
- Release 发布时间：2024-12-20T02:08:19Z（GitHub release v5.0.0）
- 许可证：MIT（LICENSE.txt，Copyright (c) 2024 Barak Shoshany）
- 源码 tarball：`https://github.com/bshoshany/thread-pool/archive/refs/tags/v5.0.0.tar.gz`
- SHA-256：`617a8fbc2c360577f498998f336777c73d581810831d4ce9c920f11ec680b07b`（tarball 实测）

## 结构
- 单文件头文件库：`include/BS_thread_pool.hpp`（v5.0.0 重新回到 true single-header）
- 无 CMake 项目（上游用脚本 compile_cpp.py + pyproject.toml 编译测试，无顶层 CMakeLists.txt）
- C++17/20/23 兼容；可选 C++20 module（modules/BS.thread_pool.cppm），本地打包按 header-only 处理
- 上游测试：`tests/BS_thread_pool_test.cpp`（单文件主程序，需 clang++/g++ 直接编译运行）
- 依赖：无任何第三方依赖（仅标准库；原生扩展 BS_THREAD_POOL_NATIVE_EXTENSIONS 为可选非必需）

## 首轮 Adapt / 本地验证
- 待执行：clang++ 编译 test_package smoke test + 上游 BS_thread_pool_test.cpp 编译运行
---

**编译结束**: 2026-08-30 09:33
**最终状态**: built
