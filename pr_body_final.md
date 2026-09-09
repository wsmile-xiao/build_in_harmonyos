- **三方库名称**：nanoflann
- **上游版本**：1.12.1
- **上游仓库地址**：https://github.com/jlblancoc/nanoflann
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 45 | 上游 tests/ GTest 套件实测：test_kdtree_basic.cpp 12 + test_kdtree_dynamic.cpp 11 + test_kdtree_incremental.cpp 22，构建为单一可执行目标 nanoflann_unit_tests；零依赖原则下未移植 |
| 集成测试 | 0 | 上游无独立集成测试 |
| 其他测试 | 0 | 上游 examples/ 为示例程序，非测试用例 |
| 合计 | 45 | 未移植上游测试 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 2 | +2 | test.cpp：KD-tree 建树与 kNN 最近邻索引/平方距离断言 |
| 鸿蒙特有测试 | 7 | +7 | test_hmos.cpp：kNN、radiusSearch、rknnSearch 断言 |
| 合计 | 9 | +9 | 实体消费者 API 测试断言，CI L1 实跑通过 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游 tests/ 实测含 45 个 GTest 单元测试用例（test_kdtree_basic.cpp 12 + test_kdtree_dynamic.cpp 11 + test_kdtree_incremental.cpp 22 = 45，与审核方实测 N=45 一致），全部用例经 tests/CMakeLists.txt 构建为单一可执行目标 nanoflann_unit_tests，未移植的逐条归因与证据如下：

1. GTest 硬依赖：45 个用例全部为 TEST() 宏，入口为 test_main.cpp（InitGoogleTest/RUN_ALL_TESTS）；tests/CMakeLists.txt 要求 bundled tests/gtest-1.8.0 或 find_package(GTest REQUIRED)，无 GTest 无法构建；
2. Threads 硬依赖：tests/CMakeLists.txt 中 find_package(Threads REQUIRED) 并链接 Threads::Threads；
3. examples 头依赖：tests/test_helpers.h 引入 ../examples/utils.h 与 ../examples/KDTreeVectorOfVectorsAdaptor.h，测试编译依赖上游 examples/ 目录源码；
4. 交付形态约束：本包为零依赖 header-only 交付物（配方无 requires，NANOFLANN_BUILD_EXAMPLES/NANOFLANN_BUILD_TESTS=OFF，证据见 test_package/MANIFEST.yml 的 upstream_test_evidence 字段），上游测试属非交付测试目标，引入 GTest 将破坏零依赖交付原则；

上游源码未做任何修改，未添加补丁。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **上游测试覆盖情况**：上游存在 45 个 GTest 用例，因 GTest/Threads/examples 头依赖未移植（逐条归因见上游测试用例修改说明）
> - **新增消费者测试**：为在鸿蒙目标环境实证核心 API，另新增 2 个测试源共 9 条断言，CI L1 实跑通过
> - **新增测试文件清单**：
>   1. `test_package/test.cpp` — 二维点云构造、KDTreeSingleIndexAdaptor 建树、findNeighbors 最近邻索引与平方距离断言
>   2. `test_package/test_hmos.cpp` — HarmonyOS aarch64 路径 kNN、radiusSearch（半径内命中 3 点）、rknnSearch（平方半径上界内返回最近点）断言

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/45（0%），上游 GTest 测试未移植，属有具体技术原因的情形（GTest/Threads/examples 硬依赖与零依赖交付原则，逐条归因见上游测试用例修改说明）
- 新增测试用例通过率：9/9（100%）

声明上游用例数 45 与实测一致（test_kdtree_basic.cpp 12 + test_kdtree_dynamic.cpp 11 + test_kdtree_incremental.cpp 22），无少报。

本地 `conan create archives/n/nanoflann/1.12.1 -pr:h ci/conan/profiles/ohos-aarch64 --build=missing` 已完成，配方和 test_package 均编译通过。本地 OHOS noexec 环境不能执行目标 ELF，Conan test 阶段按 explicit 规则跳过运行；CI 在目标环境完成运行验证（CI #40698、#40701、#41104 全步骤通过，L0/L1 门禁通过）。

## 补充说明

- 任务来源：智能任务平台依赖项任务，平台绑定 PR 关联。
- 认领时间：2026-09-05。
- 任务分支：feat/nanoflann-1.12.1。
- 基点 commit：fbdf28f08679e33ce29f2f0da76e6059b37de652。
- 依赖说明：nanoflann 为 header-only C++ 库，无 Conan 依赖；消费者测试仅使用标准 C++17 和被测包 API。
- 已知限制：本地 OHOS noexec 沙箱无法运行 aarch64 OHOS ELF；源码仓库仅保留配方、测试和元数据，不产生库二进制文件。
