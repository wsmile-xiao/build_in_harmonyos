# libfort 0.4.2 适配笔记

## 阶段状态
- **bootstrap（2026-08-31）**：仅完成 worktree/分支初始化、官方来源核验、最小归档/配方骨架。
- adapt / 编译 / W3 / finish 尚未执行（任务边界：bootstrap 阶段不进入编译）。

## 官方来源核验
- 官方仓库: https://github.com/seleznevae/libfort
- 官方标签: v0.4.2（annotated tag，2020-11-13，tagger seleznevae）
- 标签指向 commit: b1c32b67511f4612996b287a1ef4a9df012521d2
- 源码 tarball: https://github.com/seleznevae/libfort/archive/refs/tags/v0.4.2.tar.gz
- sha256: 8f7b03f1aa526e50c9828f09490f3c844b73d5f9ca72493fe81931746f75e489
- 解压后版本宏: fort.h 中 LIBFORT_VERSION_STR="0.4.2"，CMakeLists project(libfort VERSION 0.4.2)

## 构建系统
- CMake（cmake_minimum_required 3.0）
- 库目标: `fort`（lib/CMakeLists.txt: add_library(fort fort.c)，输出 libfort.so/libfort.a）
- 测试: FORT_ENABLE_TESTING=ON 时启用 ctest（tests/ 目录，bb_tests / main_test.c 等）

## 待办（adapt 阶段）
- 在真机构建环境执行 init-build / conan 验证
- 补充 test_package 实测证据
---

**编译结束**: 2026-08-31 23:37
**最终状态**: built
