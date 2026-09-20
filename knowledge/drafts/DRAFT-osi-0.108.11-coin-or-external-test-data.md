# DRAFT-osi-0.108.11-coin-or-external-test-data — COIN-OR 系上游测试依赖独立数据仓 Data-Sample/Data-Netlib

- **知识 ID（草稿）**：DRAFT-osi-0.108.11-coin-or-external-test-data
- **路径**：Path B（知识库扩展）
- **来源事件**：osi 0.108.11 上游 unitTest 首次运行 Signal 11 崩溃
- **日期**：2026-09-16

## 问题

上游 `Osi/test/unitTest` 首次运行时直接崩溃：

```
Coin6001E Unable to open mps input file ../../Data/Sample/exmip1.mps
*** osirowcutSolverInterface testing issue: read MPS failed
Signal 11 (core dumped)
```

表面像平台/架构问题（arm64-ohos），实际是测试数据缺失。

## 根因

1. COIN-OR 家族（Osi/Clp/Cbc/CoinUtils/Symphony 等）把测试数据放在独立仓库
   `coin-or-tools/Data-Sample` 与 `coin-or-tools/Data-Netlib`
   （`.coin-or/Dependencies` 声明 stable/1.2），官方 release tarball 只含源码。
2. `unitTest.cpp` 用 `-mpsDir`/`-netlibDir` 参数定位数据；缺数据时
   `OsiRowCutDebugger` 等空接口路径进入 `readMps` 失败分支。
3. 部分套件（OsiRowCut/OsiColCut 的 consistent 检查、Vol 求解器空 LP）在数据
   缺失时直接访问无效状态 → SIGSEGV（Signal 11），掩盖真实原因。

## 方案

1. 从官方仓下载测试数据：
   - Data/Sample：`https://raw.githubusercontent.com/coin-or-tools/Data-Sample/stable/1.2/exmip1.mps`
   - Data/Netlib：`https://github.com/coin-or-tools/Data-Netlib/archive/refs/heads/stable/1.2.tar.gz`
2. 运行：`Osi/test/unitTest -mpsDir=../../Data/Sample -netlibDir=../../Data/Netlib -testOsiSolverInterface`
3. 测试数据属验证证据，不进入配方交付物（非 conandata/补丁内容）。

## 验证（osi 0.108.11 实测）

| 状态 | 结果 |
|---|---|
| 缺数据首次运行 | Signal 11（`Unable to open mps input file ../../Data/Sample/exmip1.mps`） |
| 补 Data-Sample 重跑 | "All tests completed successfully"（607 PASSED / 0 FAIL，exit 0） |
| 再补 Data-Netlib + -testOsiSolverInterface | 同样 exit 0（含 Netlib 套件） |

完整命令与退出码见 osi 适配 logs（unitTest 两轮运行日志）。

## 适用边界 / 反例

- **适用**：全部 COIN-OR 系 autotools 库的上游测试（Osi/Clp/Cbc/CoinUtils/Symphony）。
- **反例**：CMake ExternalData 项目（ITK 等）走 E379 方案；仅网络真实不可达时才把
  测试数据视为不可恢复，且必须记录查询命令与时间（本轮 GitHub 可达）。

## 查重差异（相对既有条目）

| 轴 | 结果 |
|---|---|
| exact_duplicate | 0（无同条目） |
| causal_duplicate | 0 |
| trigger_overlap | 0 |
| solution_overlap | 0 |
| combination_novelty | 1（独立数据仓 × COIN-OR autotools 系） |
| boundary_novelty | 1（COIN-OR 系边界） |
| test_migration_novelty | 1（测试数据迁移/补全） |

关系：similar_to=[E379]；caused_by=[]；prerequisite_of=[]；conflicts_with=[]。
