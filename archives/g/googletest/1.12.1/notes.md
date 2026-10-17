# googletest 1.12.1 适配笔记

## 概述

- 库：googletest（GoogleTest + GoogleMock，C++ 测试/模拟框架）
- 版本：1.12.1（官方 release-1.12.1，2022-06-30 发布）
- 官方源：https://github.com/google/googletest
- 归档路径：archives/g/googletest/1.12.1/

## 来源核验（2026-08-31）

- 正式标签：`release-1.12.1`
- release commit：`58d77fa8070e8cec2dc1ed015d66b454c8d78850`（GitHub API 核验）
- 目标分支：v1.12.x
- tarball：https://github.com/google/googletest/archive/refs/tags/release-1.12.1.tar.gz
- sha256：`81964fe578e9bd7c94dfdb09c8e4d6e6759e19967e397dbea48d1c10e45d0df2`
- 说明：github.com 直连在本环境不可达（curl 28 超时），经 gh-proxy.com 镜像逐字节透传下载；
  标签/commit 由 GitHub REST API 核验一致，CMake 内 `GOOGLETEST_VERSION 1.12.1` 复核一致。

## 构建要点

- 构建系统：CMake；零外部依赖；C++17
- 产出：静态库 `libgtest.a` / `libgtest_main.a` / `libgmock.a` / `libgmock_main.a`
- 关键 CMake 开关：`BUILD_GMOCK=ON`、`INSTALL_GTEST=ON`、`BUILD_SHARED_LIBS=OFF`（静态）
- 上游测试：`gtest_build_tests=ON`、`gmock_build_tests=ON`（本地验证用）
- 参考配方：archives/g/gtest/1.17.0/conanfile.py（同库更新版本的既有配方）

## 未完成项（本轮边界）

- 首轮 Adapt 本地验证（smoke test + 上游 CTest）→ 见任务 4
- conan create / conan-verify（G2）/ W3 / finish / submit / PR：均属后续阶段，按任务边界本阶段不执行
---

**编译结束**: 2026-08-31 21:38
**最终状态**: built
