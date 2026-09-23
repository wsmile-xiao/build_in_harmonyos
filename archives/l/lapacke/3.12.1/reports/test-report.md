# lapacke 3.12.1 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device（HM 设备原生构建）
- 设备 hnp clang 15（/data/service/hnp/bin/clang，profile tools.build:compiler_executables 指定）
- Conan 2.29.1（OHOS 适配版），profile ci/conan/profiles/ohos-aarch64
- 依赖：lapack/3.12.1（ohpcd 制品仓已发布二进制，含 liblapack/libblas/libFortranRuntime/libFortranDecimal 静态库）

## Verification

- `conan-verify lapacke 3.12.1`（finish step 4）：exit 0，G0/G1/G2/G3/G4/L5 全 PASS，verdict=PASS
  - 报告：archives/l/lapacke/3.12.1/reports/conan-verify-report.md（配方 revision 23de0d455c694663918d0daf321049a2）
  - conan create 日志：archives/l/lapacke/3.12.1/reports/conan-create.log
- `CI_PACKAGES=archives/l/lapacke/3.12.1 ci/conan/build_and_test.sh`（W3 本地 CI 模拟，与 CI 同源）：exit 0
  - L0_RESULT=pass: all checks passed
  - L1_RESULT=pass: test_package executed
  - L2_RESULT=skip: no bin/ dir（纯库包无可执行产物，平台 smoke 规则跳过）
  - L4_RESULT=pass: patches clean
  - L5_RESULT=pass: lib/ has content
  - Build Summary：Total 1，Success 1，Pass rate 100.0%
  - 日志：archives/l/lapacke/3.12.1/reports/w3-local-ci.log

## 上游测试（build() 内真实执行，N=4）

上游资产：LAPACKE/example/Makefile `all` 目标 4 个演示程序（example_DGESV_colmajor、
example_DGESV_rowmajor、example_DGELS_colmajor、example_DGELS_rowmajor）。
构建日志确认行：

```
lapacke/3.12.1: upstream LAPACKE examples executed: 4/4 (upstream links with FC;
CC used for this lightweight default path — deviation documented)
```

- Test cases: 4
- Passed: 4
- Failed: 0
- Skipped: 0

说明：上游入口以 $(FC) 链接后就地执行；本配方以设备 CC 链接同一批库（编译对象、
头文件、被链库与上游一致，链接器一处偏差，同 liblapacke 0.3.30 先例），上游测试
源码零修改、零跳过。

## test_package（消费者真机执行）

test_package/conanfile.py 以设备 clang 编译 test.c 并链接 liblapacke.a 与
lapack/3.12.1 静态库（-llapacke -llapack -lblas -lFortranRuntime -lFortranDecimal
-lm），经 CONFIG_SHELL 就地执行 `./test_probe`。构建日志确认行：

```
结论 PASS：8 项断言，0 项失败
```

8 项断言：LAPACKE_ilaver 版本锚定（v3.12.1 tag 版本字符串未更新，实测 3.12.0）、
LAPACKE_dgesv 列主序/行主序解线性方程组、LAPACKE_dpotrf+dpotrs Cholesky 分解与
三角求解、LAPACKE_dgels 超定最小二乘、LAPACKE_dsyev 对称特征值分解（含特征向量
残差校验）、LAPACKE_dgetrf 奇异负例（info=2）、LAPACKE_dpotrf 非正定负例（info=2），
逐项校验数值结果而非仅解析符号。

- Test cases: 1
- Passed: 1
- Failed: 0
- Skipped: 0
- Assertions: 8 passed, 0 failed

## Result

配方在 OpenHarmony aarch64 真机上完成 conan-verify 与 W3 本地 CI 模拟双重验证，
上游测试 4/4、消费者测试 1/1（8 项断言全过），具备 built 状态（发布状态需合并后
release 流水线上传证据）。
