# Test Report — coinor-vol 1.5.4

**Date**: 2026-09-10（R03 修正）
**Build System**: autotools（COIN-OR 递归 configure：顶层 + Vol/ 子目录）
**Platform**: HarmonyOS PC (aarch64, clang-15, libc++, conan ohos-aarch64 profile)

## Test Results（双口径台账摘要，详见 reports/upstream-test-ledger.md）

**上游源码声明独立用例数 (source_declared_total)**: 3（R03 修正：rowcut / colcut / osivol，均位于 osiUnitTest.cpp main()）
**当前配置可执行用例数 (configured_executable_total)**: 3
**实际执行并通过 (executed_passed_total)**: 3
**未运行/未实例化**: 0
**全量通过率**: 3/3 = 100%（`executed_passed_total/source_declared_total`；当前配置可执行集合通过率同 3/3 = 100%）

| 入口 | 源码声明 | 构建条件 | 构建目标 | 执行结果 |
|------|---------|---------|---------|---------|
| 1 rowcut | osiUnitTest.cpp:52 `OsiRowCutUnitTest` | COIN_HAS_OSITESTS（R03 配方加 coin-or/coinutils 依赖 + --with-osi-* 生效） | osiUnitTest | 通过（EXAMPLE 读取/求解正常，无 ERROR） |
| 2 colcut | osiUnitTest.cpp:57 `OsiColCutUnitTest` | 同上 | osiUnitTest | 通过（无 ERROR） |
| 3 osivol | osiUnitTest.cpp:64 `OsiVolSolverInterfaceUnitTest` | 同上 | osiUnitTest | 通过（3 个 ERROR 均为上游设计内 expected，rc=0，`All tests completed successfully`） |

- 依赖解决：官方 `https://www.coin-or.org/download/source/Data/Data-1.0.7.tgz`
  （HTTP 200，SHA-256 `81c255641109c6da02ecc3729b4a0d02f475d1dd39e6bb2bbd2a74adde128c36`，
  内含 Sample/exmip1.mps），以 `-mpsDir=<Data-1.0.7>/Sample -netlibDir=<Data-1.0.7>/Netlib`
  实际运行全部 3 个用例（日志 SHA-256 `9ac3de069cfa1b7133762c833646e0965c29361baf0e1034c0cb28a5acd7b42c`）
- R02 曾报 0/1 (0%)（少报 N=1 + 外部数据阻塞）；R03 修正为 3/3 (100%)

## 本地真实验证（全部通过）

1. **本地编译 + 安装** (rc=0): `./configure && make -j1 && make install` → libVol.a、include/coin/VolVolume.hpp、lib/pkgconfig/vol.pc
2. **make check** (rc=0): 顶层递归构建库
3. **上游测试 osiUnitTest 构建 + 实跑** (rc=0): R03 配方显式 `make -j1 -C Vol/test osiUnitTest`，
   3 个入口全部实例化并实际运行（见上表与 upstream-test-ledger.md 第三节）
4. **Conan 配方门禁** (conan create, rc=0): R03 修复后完整 conan create 通过
   （含 coin-or/0.108.12 + coinutils/2.11.13 依赖解析、0006 bind2nd 补丁、
   osiUnitTest 构建），test_package 消费者测试 1/1 Passed
5. **HarmonyOS 专项测试** (tests/ohos_test.cpp, rc=0): 真实调用 VOL_problem::solve 求解单约束 LP，
   输出 `OHOS TEST PASS ... (value=0.000000 dual[0]=0.000000 primal[0]=0.835282 viol[0]=0.164718 rc=0)`
   （R03 复验日志 SHA-256 `6621d72c5d8d999a966ffea4f129416d0b1bcba7424fbe95afe0c131fe3595af`）

## 结论

核心库适配（编译/安装/消费者验证/专项测试）全部通过；R03 修正上游测试双口径为
3/3 (100%)，解决官方 Data 依赖并实跑全部 3 个上游用例，赛事 PR 审查 rule4 两项
（少报、缺依赖）均已闭环。