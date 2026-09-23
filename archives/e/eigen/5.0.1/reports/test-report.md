# Eigen 5.0.1 测试报告

| 类别 | 总数 | 通过 | 失败 | 结果 |
| --- | ---: | ---: | ---: | --- |
| 上游 CTest（WSL Ubuntu-D） | 1255 | 1255 | 0 | PASS |
| Conan Windows test_package | 1 | 1 | 0 | PASS |
| OHOS 真机 smoke（r006） | 2 | 2 | 0 | PASS |

## 证据

- `F:\HarmonyPC\eigen-5.0.1-adapt-20260908\evidence\wsl-upstream-ctest-final.log`
- `F:\HarmonyPC\eigen-5.0.1-adapt-20260908\evidence\conan-create-rerun.log`
- `F:\HarmonyPC\eigen-5.0.1-adapt-20260908\w3-run-r006\output\status-after-launch.log`
- `F:\HarmonyPC\eigen-5.0.1-adapt-20260908\w3-run-r006\receipts\01-TRANSFERRED.receipt` through `11-RELEASED.receipt`

首次全量 CTest 的随机失败已在独立复跑中通过；最终全量日志为同一构建目录的 1255/1255 结果。
