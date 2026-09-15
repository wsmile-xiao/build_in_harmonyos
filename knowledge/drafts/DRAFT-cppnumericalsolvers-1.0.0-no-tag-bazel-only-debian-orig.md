# DRAFT-cppnumericalsolvers-1.0.0-no-tag-bazel-only-debian-orig

> Contributor: 2301_76770579 | Status: Draft | Updated: 2026-09-09
> Source: cppnumericalsolvers 1.0.0 HarmonyOS PC 适配（上游无 tag + 仅 Bazel → Debian orig + 直编 gtest）

## 现象

1. 任务要求 cppnumericalsolvers 1.0.0，但上游 git 仓 **没有 v1.0.0 标签**
   （`git ls-remote --tags` 只有 v1.0.0alpha1/v1.0.0alpha2/v2.0.0），
   codeload 的 v1.0.0 URL 404。
2. 上游只提供 Bazel 构建，WORKSPACE 用 http_archive **联网**拉 gtest/eigen，
   构建沙箱无网络不可用；无 CMake、无 autotools。

## 根因

- 1.0.0 是 Debian 打包时认定的版本号（Debian sid 收
  `cppnumericalsolvers_1.0.0.orig.tar.gz`），上游自己从未打过这个 tag。
- header-only 库作者只维护 Bazel 工作流。

## 解决方案

1. **源码取 Debian pool orig tarball**（sha256 锁定于 conandata.yml，
   manifest 如实注明版本来源），不虚构 git URL。
2. **header-only 无需构建系统**：build() 内用 Conan gtest/1.17.0 直接编译
   `src/test/verify.cpp` 并实跑（16 TEST + 23 TYPED_TEST，typed 双精度
   实例化共 78 个 gtest 实例）。include 用仓库根（源码写
   `"include/cppoptlib/..."`）。
3. 老代码的 `TYPED_TEST_CASE` 在 gtest 1.17 仍是合法 deprecated 别名，
   无需改写。
4. `benchmark.cpp` 是性能基准（依赖 google benchmark + 写死 bazel 相对
   include），非功能测试，如实上报不纳入。

## 禁止策略

- 不得用 `github.../archive/refs/tags/v1.0.0` 作源——404，暴露未核实。
- 不得跑 bazel——WORKSPACE 联网拉依赖，沙箱必失败。
- 不得把 benchmark.cpp 计入功能测试——性质虚报 + 编译失败。

## 适用范围

git 仓标签与发行版版本号脱节（Debian 自创版本号）+ 只提供 Bazel/联网
依赖拉取的 header-only 库：Debian pool 取源 + 绕过构建系统直编测试。
