# tsl-robin-map 1.3.0 适配笔记（进行中）

> 上游：https://github.com/Tessil/robin-map（Tessil）。header-only C++11
> hash map / hash set，CMake INTERFACE 库，目标 `tsl::robin_map`，
> `find_package(tsl-robin-map)`。与已有 robin-map 1.4.1（archives/r/robin-map）
> 同上游，配方模式可复用。

## Bootstrap 核验（R02, task_id=tsl-robin-map-1.3.0-r02-pc3-2-20260901T054524Z）
- 官方 release tag v1.3.0 存在（GitHub API：target_commitish=master, published 2024-04-20）
- 官方 tarball SHA-256: a8424ad3b0affd4c57ed26f0f3d8a29604f0e1f2ef2089f497f614b1c94c7236
- 源码结构：include/tsl/{robin_map,robin_set,robin_hash,robin_growth_policy}.h
- 上游测试：tests/（Boost.Test），5 个 TU，main.cpp + 4 组测试
- 依赖：无运行时依赖；测试依赖 Boost 源码头文件
---

**编译结束**: 2026-09-01 18:18
**最终状态**: built
