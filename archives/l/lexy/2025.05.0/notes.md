# lexy 2025.05.0 — bootstrap notes

## 来源核验（2026-08-31）

- 官方仓库: https://github.com/foonathan/lexy（存在，master CMakeLists 200，project VERSION 2025.05.0，SPDX BSL-1.0）
- 官方 tag: `v2025.05.0`（GitHub release，2025-05-29 发布；releases.atom 中 release 序列含 v2025.05.0）
- tarball: `https://github.com/foonathan/lexy/archive/refs/tags/v2025.05.0.tar.gz`
- sha256: `ae867846b890b7564d633cf28d39dfc4938fe7c54515126f720c1762de5eab30`（实测 codeload 下载值）

## 构建结构

- 核心 header-only：`lexy_core` / `lexy_dev` / `lexy_unicode` / `lexy_ext` / `lexy` / `_lexy_base`（INTERFACE）
- STATIC target：`lexy_file`（源文件 `src/input/file.cpp`，link `foonathan::lexy::dev`）
- 实验性：`lexy_experimental`（INTERFACE，LEXY_EXPERIMENTAL=1）
- 公开头文件：`include/lexy/`（121 files）+ `include/lexy_ext/`
- 上游 CMake install NAMESPACE `foonathan::`，config 文件 `lexyConfig.cmake`；find_package(lexy) + foonathan::lexy
- 测试：CMake + doctest（FetchContent 拉取 doctest v2.4.12），`tests/lexy` `tests/lexy_ext` `examples`；CTest: lexy_test / lexy_ext_test / calculator / email / ip / json / shell / xml / turing
- 无外部运行/编译依赖

## Bootstrap 状态

- 专用 worktree: /storage/Users/currentUser/junshi_liu/worktrees/pc3-44-lexy-2025.05.0（分支 feat/lexy-2025.05.0，HEAD 5292d3091）
- 已建立最小归档/配方骨架（manifest/conandata/conanfile/test_package）
- 未做 adapt、编译、W3、finish、commit/push（任务边界禁止）
---

**编译结束**: 2026-08-31 09:15
**最终状态**: built
