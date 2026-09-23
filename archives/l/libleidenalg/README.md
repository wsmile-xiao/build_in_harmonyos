# Leiden Community Detection Library

> C++ 实现的 Leiden 社区发现算法库，依赖 igraph。

## 简介

libleidenalg 是 Vincent Traag 开源的 Leiden 算法 C++ 实现，是 Louvain 算法的扩展，
支持 CPM、Modularity、Significance、Surprise、RBConfiguration、RBER 等多种质量函数。
核心类为 `Optimiser`（执行 Leiden 优化）与 `MutableVertexPartition` 派生分区类。
可处理数百万节点规模的图（受内存限制）。

## OHOS 适配要点

- CMake 构建（最低要求 3.23），`find_package(igraph 1 CONFIG REQUIRED)` 定位依赖。
- 配方声明 `requires igraph/1.0.0`（transitive_headers/libs），`BUILD_SHARED_LIBS` 跟随 `shared` 选项。
- 上游 0.13.0 发布包无任何自动化测试（无 tests/、无 CTest），按 `no_tests` 路径申报；
  test_package 用 Zachary 空手道俱乐部图跑真实 CPM/Modularity + Optimiser 管线。
- 公开头经 `FILE_SET headers` 安装到 `include/libleidenalg`，导出的 CMake 目标为
  `libleidenalg::libleidenalg`，同时链接 `igraph::igraph`。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| igraph | 1.0.0 | 图数据结构与算法底座（`igraph::igraph`） |

## 功能验证

```bash
conan create archives/l/libleidenalg/0.13.0 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
./test_leidenalg  # 期望输出：all 6 checks PASSED
```

## 参考

- [上游仓库](https://github.com/vtraag/libleidenalg)
- [0.13.0 发布页](https://github.com/vtraag/libleidenalg/releases)
- [igraph 官网](https://igraph.org)
