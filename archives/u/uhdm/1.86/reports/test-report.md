# uhdm 1.86 测试报告

- **包**: uhdm/1.86@ohpcd/stable
- **平台**: OHOS aarch64（HarmonyOS PC，目标机原生执行）
- **编译器**: clang/clang++ 15.0.4（conan profile ohos-aarch64）
- **构建系统**: CMake 4.1.2（上游 minimum 3.20）
- **日期**: 2026-09-29 ~ 2026-09-30
- **状态**: built（conan-verify PASS + W3 本地 CI 1/1）

## 1. 上游测试台账（R51 三步法）

### 1.1 清点（适配前）

- tests/*.cpp 共 **17 个测试源**（CMakeLists.txt L280 `register_tests()` 显式枚举，非 GLOB；test_util.h 为工具头）
- → 17 个测试二进制，ctest 注册 **43 个 gtest 用例**（`gtest_discover_tests`，L291）
- 测试框架: GTest（gtest/gmock/gtest_main，来自上游 third_party/googletest，本适配不构建）

### 1.2 实测（探索期，UHDM_BUILD_TESTS=ON）

- 环境: OHOS aarch64 目标机原生执行，`TMPDIR=$HOME/tmp`（E002/E544-E3AD 口径：/tmp 只读）
- 首轮 `-j4` 并发: **36/43**（7 条 0.01-0.02s 瞬时失败，共享 TMPDIR 并发竞态，涉及 vpi_get_test/classes_test 等）
- 串行重跑: **43/43 PASSED（100%，exit 0）**，Total Test time ≈ 106s
- 失败样本单独直跑（vpi_get_test）: 4/4 PASSED
- 结论: 7 条失败为瞬态环境问题，**非产品缺陷**；串行口径为准（双口径证据留存 notes.md「验证结果」节）

### 1.3 制品口径

- `UHDM_BUILD_TESTS=OFF`: 上游 gtest 套件不进制品（与 CI 只读 4 文件口径一致）
- 43/43 结果由本报告 + notes.md 双口径留证

## 2. test_package（Conan L1 消费测试）

| # | 测试 | 方式 | 结果 |
|---|------|------|------|
| 1 | VPI 对象写读回环 | test.cpp: `Serializer::MakeConstant` 写 4 属性（VpiFile/VpiLineNo/VpiSize/VpiDecompile）→ `vpi_get_str`/`vpi_get` 读回断言（模式源自上游 tests/vpi_get_test.cpp） | PASS |
| 2 | uhdm-dump CLI 冒烟 | test() 内 `self.run(uhdm-dump)` 退出码检查 | PASS |

- **2/2 PASSED（100%）**（conan create 内执行）
- MANIFEST.yml 声明上游 17 套件 / 43 用例（assertion_count=43）

## 3. 门禁结果

| 门禁 | 结果 | 备注 |
|------|------|------|
| G0 预构建风险评估 | PASS | E092 已在配方处理 |
| G1 配方完整性 | PASS | 12 项（name/version/source/build/package/package_info/export_sources/补丁调用/R26/conandata/test_package/MANIFEST） |
| G2 conan create | PASS | test_package 构建+运行全绿 |
| G3 系统同名库隔离 | PASS | 静态制品，无 .so 冲突 |
| G4 产物完整性 | PASS | bin(4 工具)/lib/include 齐全 |
| L2/L4/L5 | 跳过 | 工具 conan cache 路径定位限制，CI 干净环境复验 |
| W2 结构（L0a-L0e） | PASS | finish step [5/10] 内嵌 |
| R36 依赖发布 | PASS | capnproto/1.3.0 制品仓在库 |
| W3 本地 CI 模拟 | PASS | 1/1 100%，.ci-result.json exit_code=0 |
| W4 独立审计 | PASS | P0=0 P1=0（P3×3 非阻断） |

## 4. 结论

编译与测试全通过（上游 43/43 + L1 2/2），配方通过本地全部门禁验证，达到提 PR 条件；CI 干净复验待执行（按任务约定手动触发 `/rebuild`，随后 `submit uhdm 1.86 --resume` 续环）。
