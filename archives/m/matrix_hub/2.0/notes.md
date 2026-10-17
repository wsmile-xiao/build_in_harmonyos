# matrix_hub 2.0 — 适配笔记

## 概况
- 上游：https://github.com/Amoiensis/Matrix_hub（Apache-2.0）
- 版本：2.0（tag v2.0，commit cca0543594fa8cf5473806bc61f5658892ee9321）
- 语言：C（C99），CMake 构建
- 形态：header-only INTERFACE 库（MatrixHub / MatrixHubSolvers）+ 两个 CLI 工具
  （Matrix_Hub_v2_0_cli 脚本计算器、Matrix_Hub_v2_0_solver LP/MIP 求解器）
- 依赖：无外部依赖（仅链接 libm）

## 适配要点
1. 上游 CMakeLists.txt 无任何 `install()` 规则。补丁
   `patches/0001-add-install-rules.patch` 添加 include/ 目录安装与两个 CLI 工具的
   RUNTIME 安装（MatrixHub/MatrixHubSolvers 为 INTERFACE 目标，install(TARGETS
   ... INCLUDES) 仅登记 include 目录）。
2. conanfile.py 采用 CMakeToolchain；OHOS 无 CMake platform module，按知识
   E092 将 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` 映射。
3. package_info() 中 `runenv_info.prepend_path("PATH", bin)`：CLI 工具必须注入
   PATH，否则 test_package 的 conanrun 阶段 `Matrix_Hub_v2_0_cli` 不可执行
   （实测首轮 G2 失败：`inaccessible or not found`）。
4. 配方 options.shared 保留默认 False；INTERFACE 库无 .so/.a 产物，无需 R26 静态化。
5. commands.json（软件级）声明两个 CLI 工具（R38/L0k）。

## 测试
- 上游无 ctest/pytest 注册；可运行的上游用户入口为 examples/scripts 下 11 个
  `.m` 脚本、examples/c_library/main.c 示例程序、examples/solver/problems 下
  4 个 LP/MIP 样例问题，全部实跑通过（详见 test_package/MANIFEST.yml 台账）。
- test_package：真实消费者程序 test.c（通过公开头文件调用 Matrix_gen/M_mul/
  M_I/M_print 并数值断言 A*B=[19 22;43 50]）+ 打包后的 CLI 执行上游 basic.m 脚本。

## 门禁结果
- G0 预构建风险：PASS
- G1 配方完整性：PASS
- G2 conan create（OHOS armv8, clang 15）：PASS
- G3 系统同名库隔离：PASS（无同名库冲突）
- G4 产物完整性：PASS
- L2 smoke / L4 checksec / L5 基线：见 reports/conan-verify-report.md
- W3 本地 CI（setup.sh + build_and_test.sh）：PASS（.ci-result.json 已写入）

## 知识候选台账（knowledge_candidate_ledger）

### 候选 C1：CMake header-only INTERFACE 库 + CLI 缺 install() 规则与 runenv PATH 注入
- 真实首错：`/system/bin/sh: Matrix_Hub_v2_0_cli: inaccessible or not found`（conan create G2，
  test_package conanrun 阶段 Error 127）；且上游 CMakeLists.txt 无任何 install() 规则，
  cmake.install() 产物为空。
- 根因：①上游仅声明 INTERFACE 目标与可执行文件，无 install()；②CLI 未在 package_info()
  的 runenv_info 注入 PATH，conanrun 环境找不到二进制。
- 修复：0001-add-install-rules.patch（GNUInstallDirs + install headers/bin）；
  conanfile.py `self.runenv_info.prepend_path("PATH", bin)`。
- 验证：conan-verify G2 PASS；test_matrix_hub 数值断言 1/1 Passed；
  Matrix_Hub_v2_0_cli basic.m 脚本 exit 0。
- 适用范围：CMake header-only/INTERFACE 库同时产出 CLI 工具的 Conan 打包；可跨库复用。
- 查重结论与路径决定：见下。

### 查重（七轴）
| 轴 | 结论 | 说明 |
|---|---|---|
| exact_duplicate | 否 | 无既有条目完全覆盖“install() 缺失 + runenv PATH 注入”组合 |
| causal_duplicate | 否 | E298 根因是 cmake.test() 委托 CTest；E504 是 install 期 RPATH 改写，均与本候选不同因 |
| trigger_overlap | 部分 | 与 E298/E504 共现 Error 127 / Error in test() 表面特征 |
| solution_overlap | 部分 | 与 E298 都以显式 run 为消费侧做法；本候选含生产者侧 runenv_info 注入 + install() 补丁 |
| combination_novelty | 是 | 生产者侧 PATH 注入 + install() 补丁的组合未见于既有条目 |
| boundary_novelty | 是 | 边界：纯库无 bindirs 不需注入；有 install() 上游无需补丁 |
| test_migration_novelty | 否 | 无上游测试迁移议题 |

- 关系：similar_to=E298（conanrun 环境）、E504（Error 127 特征）、E424（commands.json 元数据，同包 CLI 交付不同层）；
  caused_by=无；prerequisite_of=无；conflicts_with=无。
- 决定：**new_draft**（已建 .kv/.md 配对，可跨库复用，走路径 B【知识库扩展】）。
  非噪声候选数：1；完整复用数：0；草稿数：1；path_a_no_knowledge：不适用。
---

**编译结束**: 2026-09-28 17:34
**最终状态**: published
