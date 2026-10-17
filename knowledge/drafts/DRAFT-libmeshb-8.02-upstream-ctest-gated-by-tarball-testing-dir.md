# DRAFT-libmeshb-8.02-upstream-ctest-gated-by-tarball-testing-dir

**来源**: libMeshb 8.02 适配 HarmonyOS PC（PR feat/libmeshb-8.02）
**路径**: Path B（知识库扩展）| **状态**: 草稿（待审核 promote）

## 问题

CMake 工程常用 `option(WITH_*_CTEST)` 门控上游测试：开关 ON 时
`enable_testing()` + `add_subdirectory(testing)` 注册 ctest 用例。
但 **GitHub release tarball 可能不包含 `testing/` 目录**（该目录仅存在于 git
仓库），此时开关 ON 会让 CMake 配置阶段直接失败（`add_subdirectory` 找不到
`testing/CMakeLists.txt`），从而把「上游测试不可用」误判为「该库不能开 ctest」。

- libMeshb 7.80：tarball 无 `testing/` → `WITH_GMF_CTEST=ON` 配置失败
  （add_subdirectory(testing) 找不到目录），只能以消费者测试补位（N_static=0）。
- libMeshb 8.02：tarball 携带 `testing/` → `WITH_GMF_CTEST=ON` 配置成功，
  注册 9 个 add_test（7 个 C 用例 + 2 个 Fortran 门控，后者因 OHOS 无 Fortran
  编译器不实例化），实际运行 **7/7 通过**。

## 根因

开关可用性由 **tarball 内容形态**决定，与平台无关。release tarball 对测试目录的
裁剪策略（git-only 目录不进 tarball）导致 `add_subdirectory(testing)` 失败。

## 方案

1. 下载官方 release tarball 后先清点顶层目录（`tar -tzf`），确认 `testing/`
   或等价测试目录是否存在。
2. 存在 → 配方 `generate()` 置 `WITH_*_CTEST=ON`，`build()` 后以 `ctest -N`
   枚举注册数、`ctest --output-on-failure` 实际运行，按**双口径**上报：
   - `source_declared_total` = add_test 声明总数（含门控项）
   - `configured_executable_total` = 当前工具链实际注册数
   - `executed_passed_total` = 实际运行通过数
   - Fortran/MPI 等门控未实例化项如实单列，不得写成失败或已通过。
3. 不存在 → 开关保持 OFF，notes.md 记录清点证据，以 test_package 消费者测试
   补位；不得把「tarball 缺目录导致配置失败」写成平台限制或外部阻塞。

## 验证

- libMeshb 8.02 OHOS aarch64：`WITH_GMF_CTEST=ON` 配置成功；`ctest -N` 注册
  7 项；`ctest` 运行 7/7 Passed（0.22s）；日志 sha256
  `c59284318f1d5332b3affc89258e818e8600bc67b21508c21d3b167b6e391a66`。
- 反例证据：7.80 同开关 ON 配置失败（tarball 无 testing/）。

## 适用边界

- 适用：CMake 工程以 `option(WITH_*_CTEST)` 门控 `add_subdirectory(testing)`
  且以 GitHub release tarball 发布（测试目录可能被裁剪）的 C/C++ 库。
- Meshb 系列（Mmg/ParMmg 同族）与同类 tarball 裁剪策略库适用。
- 不适用：git 源码直接构建（testing/ 恒存在）；Conan source() 已含 testing/；
  autotools make check 类框架（见 DRAFT-10251 系规则）。

## 关系

- `similar_to`: E535（CGNS 上游 CTest 启用与真实通过率核验）
- `caused_by`: release tarball 对测试目录的裁剪策略
- `prerequisite_of`: 上游测试双口径统计的真实分母（source_declared_total）
