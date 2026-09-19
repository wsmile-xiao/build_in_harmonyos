# libecpint 1.0.7 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device（`ssh hm`，HOME `/storage/Users/currentUser`）
- Clang 15（OHOS SDK，profile `ci/conan/profiles/ohos-aarch64`，os=OHOS / aarch64 / libc++ / cppstd 17）
- Conan 2.29.1（OHOS 适配版，`/storage/Users/currentUser/usr/local/bin/conan`）
- 上游源码：github.com/robashaw/libecpint v1.0.7 tag 归档，
  sha256 `e9c60fddb2614f113ab59ec620799d961db73979845e6e637c4a6fb72aee51cc`

## Verification（正式轮，finish built，私有 CONAN_HOME）

- `conan-verify`（G0–G4 + L2/L4/L5）：PASS（G2 为干净 `conan create`，报告
  `reports/conan-verify-report.md`）
- 本地 CI 模拟（与 CI 同源脚本 `setup.sh` + `build_and_test.sh`）：exit 0，
  `.ci-result.json` `exit_code=0`（integrity_hash `aa27ef95bec8b6b5`，
  log_sha256 `5b2268932b75b3cc8197725a71be6c6eb879edcff0ff3429df87532faae4d802`），
  原件 `reports/w3-local-ci.log`
- W2 结构检查（L0a–L0e）：PASS；R36 依赖检查：pugixml/1.15-r0、gtest/1.17.0 均
  可从制品仓 download（W0 回执 `w0.json`）

## 上游测试实跑结果（R2 修订：用例级口径）

> 口径修订说明：本报告 R1 版按"可执行测试项 18"（17 项 ctest 注册 + 1 个
> StressTest 自定义目标）计数，外部审查按 gtest 用例口径实测 53 判少报。
> R2 起统一为：**单元测试按 gtest 用例（TEST/TEST_F/TEST_P 宏实例）计，
> 集成测试按独立程序计**，合计 64。

来源：正式轮 `w3-local-ci.log` 中的真实 ctest 与构建输出（非手工填写）。

- ctest：`100% tests passed, 0 tests failed out of 17`
  - tests/lib 10 个 benchmark 程序（IntTest1、IntTest2、DerivTest1、DerivTest2、
    HessTest1、HessTest2、APITest1、APITest2、Type1Test1、Type1Test2，
    benchmark 逐值对照，阈值 1e-5）
  - tests/units 7 个 gtest 程序，覆盖 **53 个 gtest 用例**（mathutil 7、
    multiarr 13、bessel 7、gshell 8、ecp 11、generate 3、gaussquad 4；
    gaussquad 为 4 个 TEST_P × 2 组参数，实跑展开为 8 个实例，7 程序共 57 个
    运行实例；ctest 按程序退出码判定，任一 gtest 用例失败即非零退出）
- StressTest 自定义目标（POST_BUILD 压测）：
  `HMBS_STRESS_TEST_RESULT={"status": "passed", ..., "discovered": 1, "executed": 1, "passed": 1, "failed": 0}`
- 合计：N=64（53 gtest 用例 + 10 benchmark 程序 + 1 压测程序），
  N′=64，通过 64，失败 0，跳过 0

## test_package（消费者测试）

`find_package(ecpint CONFIG REQUIRED)` + 链接 `ECPINT::ecpint`，按包内安装
头文件复现上游 IntTest1 基准的 (A,A) shell pair（ECP 5 原函数 + 双
GaussianShell + `ECPIntegral(3,4)`），9 个积分值逐项对照上游 benchmark
（1e-7，严于上游 1e-5），并校验安装的 config.hpp 暴露 `LIBECPINT_MAX_L=5`。

- Test cases: 1（4 组断言）
- Passed: 1
- Failed: 0
- Skipped: 0
- 证据：`ALL CONSUMER CHECKS PASSED`（`w3-local-ci.log`）

## Result

配方在 OpenHarmony aarch64 真机上完整验证（编译 + 上游 64 项全过 + 消费者
测试通过），状态 built；发布（upload）待合并后 release 流水线。
