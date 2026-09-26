# E322-draft-392D — CPMAddPackage 依赖在禁网 CI 下用 SOURCE_DIR 分支本地化

> **Contributor**: pc1-14 | **Status**: DRAFT | **Updated**: 2026-09-22
> **Severity**: 🟡 medium | **Category**: cmake / network / test / portability
> **触发事件**: cxxgraph 4.1.0 适配（header-only 图算法库，上游 302 个 TEST 声明 / 301 个注册）

## 错误特征

```
CPM: error: Failed to download ...
fatal: unable to access 'https://github.com/...'
Downloading CPM.cmake to <build>/cmake/CPM.cmake   # 顶层 CMakeLists 配置期直连 GitHub
```

上游 CMake 项目用 **CPM.cmake** 拉取依赖（尤其测试框架 googletest/zlib），CI worker
无法直连 github.com；且上游**未设** `CPM_USE_LOCAL_PACKAGES`，`CPMAddPackage` 一律走
`GITHUB_REPOSITORY` 下载，configure 阶段即失败。顶层 CMakeLists 还可能配置期直连
GitHub 下载 CPM.cmake 引导脚本本身。

## 根因

- CPMAddPackage 默认从 GitHub 克隆/下载；禁网环境必然失败
- 上游未声明 `CPM_USE_LOCAL_PACKAGES ON`（零 patch 路线不可用，见既有草稿
  `DRAFT-cmake-cpm-addpackage-local-package-offline`）
- 顶层 CMakeLists 的 `file(DOWNLOAD .../CPM.cmake)` 也是网络依赖点

## 推荐方案：SOURCE_DIR 分支 + conandata 预下载（patch 路线）

给上游 CPMAddPackage 增加本地源分支（保留原下载回退），配方侧：

1. **conandata.yml** 增加 `gtest_sources` / `zlib_sources` / `cpm_source` 条目
   （官方 HTTPS URL + sha256）
2. **conanfile.py `build()`** 预下载解压到 `build_folder/<pkg>_src`，
   CPM.cmake 预下载到 `build_folder/cpm/cpm/CPM.cmake`
3. **conanfile.py `generate()`** 注入 cache_variables：
   - `CXXGRAPH_GTEST_SOURCE_DIR` / `CXXGRAPH_ZLIB_SOURCE_DIR` → 本地源码
   - `CPM_SOURCE_CACHE` → build_folder/cpm（CPM 引导脚本查找点）
   - `CMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake 4.x 兼容，见 DRAFT-E321）
4. **patch** 上游 `test/CMakeLists.txt`：`if(DEFINED <PKG>_SOURCE_DIR AND EXISTS ...)`
   用 `SOURCE_DIR`，`else()` 保留原 `GITHUB_REPOSITORY` 回退

## 关键陷阱

| 陷阱 | 说明 |
|------|------|
| `tc.variables` vs `tc.cache_variables` | 工具链文件在 cmake_minimum_required 之后才 include，`variables` 对 CPM 判断无效；必须 `cache_variables`（-D 命令行，最优先） |
| `<Pkg>_DIR` 是 CMake 包名 | SOURCE_DIR 分支方案不依赖 config 生成，无此问题（优于 fetch→find_package 路线） |
| CPM.cmake 引导脚本本身 | 顶层 CMakeLists 可能配置期下载 CPM.cmake；用 `CPM_SOURCE_CACHE` + 预置文件覆盖 |
| 禁止镜像域 | conandata 不得写 gh-proxy.com/ghfast.top（PF7 闸），CI 侧 build_and_test.sh 会自动注入镜像 fallback |
| 版本固定 | 上游常用 `GIT_TAG origin/main`（不可复现），本地化时固定 tag（如 googletest v1.17.0） |

## 验证（cxxgraph 4.1.0 实测）

```bash
# conan create 内 configure 命中本地源：
-- CPM: Adding package googletest@ (v1.17.0 at <build_folder>/gtest_src)
-- CPM: Adding package zlib@1.2.13 (v1.2.13 at <build_folder>/zlib_src)
# 上游测试全量运行：
[==========] 301 tests from 42 test suites ran. (1331 ms total)
[  PASSED  ] 301 tests.
```

## 适用边界

- 适用：上游用 CPMAddPackage 且未设 CPM_USE_LOCAL_PACKAGES；测试框架依赖需本地化；
  需维护补丁成本可接受（本模式补丁约 20 行，随上游版本升级需同步）
- 反例/不适用：上游已设 `CPM_USE_LOCAL_PACKAGES ON` → 零 patch 路线优先
  （DRAFT-cmake-cpm-addpackage-local-package-offline）；依赖可 conan 化并支持
  find_package → 可考虑 fetch→find_package 路线（DRAFT-cmake-test-framework-fetch-to-conan-find-package）

## 与既有条目关系

| 条目 | 关系 |
|------|------|
| DRAFT-cmake-cpm-addpackage-local-package-offline | 同场景（CPM 离线）不同解法：零 patch（CPM_USE_LOCAL_PACKAGES） vs SOURCE_DIR 分支 patch；本条目为部分覆盖 + 新增差异 |
| E017 | 网络层镜像策略（use-ghfast），非配方结构方案，无冲突 |
| DRAFT-E321 | CMAKE_POLICY_VERSION_MINIMUM=3.5（CMake 4.x），常与本方案配套使用 |
| crow 1.3.3 归档 | CATCH2_LOCAL_SOURCE_DIR 同模式先例（无独立知识条目） |
