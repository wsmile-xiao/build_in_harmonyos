# libleidenalg 0.9.0 — igraph 0.10→1.0 API 迁移 + CMakeDeps 同主版本闸

## 问题

libleidenalg 0.9.0（面向 igraph 0.10.x API）在 OHOS aarch64 上链接仓内
igraph/1.0.0 时，conan-verify G2 依次暴露三个独立首错：

1. `find_package(igraph 0.10 CONFIG REQUIRED)` 被 CMakeDeps 生成的
   `igraph-config-version.cmake` 拒绝：该文件做"同主版本"校验
   （`PACKAGE_FIND_VERSION_MAJOR STREQUAL CVF_VERSION_MAJOR`），
   请求 0.10 的 major=0 与 igraph 1.0.0 的 major=1 不匹配，即使
   1.0.0 > 0.10 也报 "Could not find a configuration file ... compatible
   with requested version 0.10"。
2. 源码 `src/GraphHelper.cpp` 用 igraph 0.10 签名调用
   `igraph_neighbors(graph, neighs, v, mode)`（4 参）与
   `igraph_incident(graph, edges, v, mode)`（4 参），igraph 1.0 中
   `igraph_neighbors` 为 6 参（新增 `loops` 与 `multiple`）、
   `igraph_incident` 为 5 参（新增 `loops`），编译报 no matching function。
3. 上游 `include/CMakeLists.txt` 的 `FILE_SET headers` 只列 10 个头文件，
   漏掉 `LinearResolutionParameterVertexPartition.h`（源码树有 11 个），
   且 0.9.0 公开头互相用尖括号同级包含
   （`CPMVertexPartition.h` 内 `#include <LinearResolutionParameterVertexPartition.h>`），
   消费者仅带 `-I<prefix>/include` 时找不到 `include/libleidenalg/` 下的同级头。

## 根因

- CMakeDeps 生成的 config-version 文件使用"同主版本"兼容策略
  （AnyNewerVersion 之上再锁 major），这是 Conan 2 CMakeDeps 的固定行为，
  不是网络或配方误配；上游 find_package 带版本下限 `0.10` 时直接撞上。
- igraph 1.0 对邻居/关联边接口做了签名扩展（loops/multiple 参数化），
  0.10 时代的 4 参调用不再匹配；IGRAPH_LOOPS_TWICE + multiple=true 等价
  保留 0.10 语义（环按两个方向各计一次）。
- libleidenalg 0.9.0 发布包的头安装清单漏头 + 同级尖括号包含，
  是上游打包缺陷，需配方级补偿（package_info includedirs）才能被消费者解析。

## 方案

三个补丁（patches/ 0001-0003）+ 配方 package_info 补偿：

1. `patches/0001-CMakeLists.txt.patch`：把 `find_package(igraph 0.10 CONFIG
   REQUIRED)` 改为 `find_package(igraph CONFIG REQUIRED)`，去掉版本下限，
   绕开 CMakeDeps 同主版本校验（0.9.0 实际只用 igraph 1.x 稳定 API）。
2. `patches/0003-src-GraphHelper.cpp.patch`：按 igraph 1.0 官方迁移语义适配：
   `igraph_incident(g, edges, v, mode, IGRAPH_LOOPS_TWICE)`、
   `igraph_neighbors(g, neighs, v, mode, IGRAPH_LOOPS_TWICE, true)`。
3. `patches/0002-include-CMakeLists.txt.patch`：把
   `LinearResolutionParameterVertexPartition.h` 补进 FILE_SET headers。
4. 主配方 `package_info()`：`self.cpp_info.includedirs = ["include",
   "include/libleidenalg"]`，让 CMakeDeps 目标同时携带
   `<prefix>/include` 与 `<prefix>/include/libleidenalg`，消费端
   `#include <libleidenalg/...>` 与头内同级尖括号包含都能解析。

## 验证

- conan-verify G0-G5 全通过（G1 配方完整性 / G2 conan create /
  G3 系统同名库隔离 / G4 产物完整性 / L2/L4/L5）。
- test_package `./test_leidenalg` 真实运行 6/6 PASS
  （Zachary 34 顶点 / 78 边 / CPM 与 Modularity 分区合法性与质量不回退）。
- W3 本地 CI 模拟（build_and_test.sh）1/1 100% PASS（JC/L0/L1/L4/L5）。

## 适用边界

- 面向"在仓依赖为大版本升级（如 igraph 1.0.0）而目标库仍是旧 API 世代"的
  CMake+Conan 库；CMakeDeps 同主版本闸对任何带版本下限的 find_package
  生效。igraph 0.10→1.0 邻居/关联边签名变化对其他 igraph 消费库同样适用。

## 反例 / 限制

- 不得把 CMakeDeps 同主版本校验当网络/注册表故障重试；先看
  igraph-config-version.cmake 的 PACKAGE_VERSION 与 major 比对。
- 去掉版本下限的前提是目标库 API 与新版依赖兼容（0.9.0 仅需 igraph 1.x
  稳定接口，编译与测试实证通过）；若 API 不兼容须逐个签名适配而非盲目降级。
- FILE_SET 漏头是上游打包缺陷，补丁是配方层最小补偿；若上游后续版本已修复，
  应删除对应补丁，勿长期保留。

## 关联

- 知识库已有 E217（airspyhf 单子目录 includedirs）方向不同：E217 是"头文件
  装进 include/<subdir> 但 includedirs 只写 include"，本条目是"同级尖括号
  包含 + FILE_SET 漏头 + 依赖大版本 API 迁移"三合一。
