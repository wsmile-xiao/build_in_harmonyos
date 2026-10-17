# redo-c 0.3 适配笔记

## 编译环境
- 构建系统: custom（上游 .do 文件自举；配方直接编译 redo.c）
- 编译日期: 2026-09-21
- 编译器: clang (OHOS profile, aarch64-linux-ohos)
- 状态: built

## 编译步骤
配方 build() 直接在 source 目录执行（等价上游 redo.do）：
```bash
clang -O2 -Wall -Wextra -Wwrite-strings -o redo redo.c
```
package() 安装 bin/redo，并按上游 links.do 创建符号链接：
redo-ifcreate、redo-ifchange、redo-always → redo。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 | 零外部依赖单文件 C 实现，无编译问题 | 直接编译 |

## 源码修改
无补丁，未改上游源码。

## 依赖版本
无（零外部依赖）。

## 验证结果
```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# conan-verify G0-G4 通过；test_package 端到端 .do 构建验证通过
```

## 上游测试枚举台账（R51 上游测试三步法）

官方 tag v0.3（commit c19b03dc）源码共 **7 个文件**，完整枚举如下：

| 文件 | 类型 | 是否独立上游用例 | 分类理由 | 是否实际运行 | 结果/原因 |
|------|------|-----------------|----------|-------------|----------|
| README.md | 文档 | 否 | 非可执行测试 | — | — |
| redo.c | 用户测试源/主源码 | 否 | 产品源码，无内嵌 TEST_CASE/自测宏 | 编译并运行 | 经 clang 编译为 redo 并运行通过 |
| all.do | 构建脚本 | 否 | redo 构建入口（`redo-ifchange redo links`），非测试 | 尝试运行 | 自举运行：需 `cc` 与 PATH 中 redo-ifchange；本环境无 `cc`（仅 clang），改用配方 clang 直编 |
| redo.do | 构建脚本 | 否 | 等价 `cc ... -o redo redo.c`，非测试 | 尝试运行 | 同上 |
| links.do | 构建脚本 | 否 | 创建 redo-ifcreate/ifchange/always 符号链接，非测试 | 运行 | 配方 package() 等价实现并通过 |
| redo-sources | 辅助脚本 | 否 | 列依赖辅助工具，非测试 | — | — |
| redo-targets | 辅助脚本 | 否 | 列可构建目标辅助工具，非测试 | — | — |

- 框架头/源码：**无**（无 ctest/pytest/doctest/catch/gtest 等任何测试框架痕迹，grep 无匹配）
- 样例/基准/fixture：**无**
- 测试脚本：**无**（redo-sources/redo-targets 为构建辅助，非测试）
- 构建目标：`redo` 可执行文件 + 3 个符号链接（产物，非测试目标）

### 双口径统计
- `source_declared_total`：**0**（官方源码按可复制枚举规则发现的独立上游测试用例数为 0）
- `configured_executable_total`：**0**（无测试入口可实例化）
- `executed_passed_total`：**0**（无上游用例可执行；0/0 分母为 0，按"上游确无测试"处理，附以上清点证据）
- 未运行/未实例化数：0（无入口存在）
- 通过率：无上游测试（0/0），不适用百分比口径；实际运行验证由鸿蒙专项消费者用例承担（见下节）

> 自举复现说明：`redo` 直接运行官方 .do 流程需要 PATH 中存在 redo-ifchange 且系统有 `cc`；本环境无 `cc`（仅 clang），属环境事实而非库缺陷。配方以 clang 直编等价实现，产物行为一致。

## 知识候选台账（knowledge_candidate_ledger）与路径决定

### 候选观察（knowledge_candidate_observation: required）

本次适配过程无编译错误、无平台阻塞、无补丁、无测试失败——候选观察记录如下：

| 候选 | 真实错误/现象 | 根因 | 修复 | 验证 | 适用范围 |
|------|--------------|------|------|------|---------|
| K1 | redo-c 官方构建为 .do 自举（all.do/redo.do/links.do），无 configure/make 标准流程 | redo 构建系统：`.do` 文件驱动，`redo.do` 等价 `cc -o redo redo.c`，`links.do` 创建 3 个符号链接 | 配方 build() 直接用 Conan clang 编译 redo.c；package() 创建符号链接 | conan create 通过；test_package 端到端通过；test_ohos ALL PASS | 使用 redo 构建系统的少量单文件 C 工具（redo-c 唯一） |
| K2 | 本环境无 `cc`（仅 clang），redo.do 内硬编码 `cc` 导致自举失败 (exit 127) | OHOS 环境无系统 `cc` 命令 | 配方从 Conan conf 取编译器（R33），不用 shell `$CC`/`cc` | 编译通过，产物运行正常 | 与 E095（自定义脚本硬编码 c++）同族的一般化：R33 已是既有铁律 |

### 七轴查重

| 轴 | 结果 | 说明 |
|----|------|------|
| exact_duplicate | 否 | knowledge/graph 与 drafts 均无 redo/.do 相关条目（grep 全库 0 命中） |
| causal_duplicate | 否 | 无其他条目的根因链与"redo .do 自举"相同 |
| trigger_overlap | 部分 | E095（自定义 configure 硬编码 c++/cc）、E097（无标准 configure/make install 的自定义构建系统）触发面部分重叠——都是"非标准构建系统 + 需手动等价构建" |
| solution_overlap | 高 | 方案（识别构建系统 → 手动直接用 clang 编译 → 安装产物）与 E097（custom-config-mk 手动构建）、2048.c（单文件 C 直接编译）方案高度同构，无方法论新增 |
| combination_novelty | 弱 | 直接编译单文件 C + 创建符号链接属常规 Conan 配方模式（2048.c 等已实例化），无新组合 |
| boundary_novelty | 无 | 未发现 redo 之外的适用边界扩展（redo 构建系统使用者极少） |
| test_migration_novelty | 无 | 无上游测试可迁移；0 上游用例结论为库自身事实，非可复用方法 |

### 关系字段

- similar_to：E095（编译器硬编码/缺失 cc/c++）、E097（自定义构建系统手动构建）
- caused_by：无（无失败链）
- prerequisite_of：无
- conflicts_with：无

### 路径决定

`path_a_no_knowledge`

理由：K1/K2 的方案与既有知识（E095/E097 + R33 + 2048.c 等大量直接编译配方）solution_overlap 高、combination_novelty 弱，未证明可跨库复用的新增知识差异——redo 是唯一使用 .do 自举的库，其"直接编译单文件 C"方案在知识库已有充分实例化，无需新建草稿（七轴查重不满足路径 B 的"存在新增差异"门槛）。
---

**编译结束**: 2026-09-21 03:23
**最终状态**: built
