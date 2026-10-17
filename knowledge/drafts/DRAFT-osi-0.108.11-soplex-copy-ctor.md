# DRAFT-osi-0.108.11-soplex-copy-ctor — COIN-OR OsiSpx 0.108.11 operator= 使用已知损坏的 SoPlex 拷贝构造触发 SIGTRAP

- **知识 ID（草稿）**：DRAFT-osi-0.108.11-soplex-copy-ctor
- **路径**：Path B（知识库扩展）
- **来源事件**：osi 0.108.11 R04 `Osi/test/unitTest`（soplex/3.1.1）copy-ctor 段 SIGTRAP
- **日期**：2026-09-18

## 问题

对 osi 0.108.11 配置 `--with-soplex`（soplex/3.1.1 已发布）后，
OsiSolverInterfaceUnitTest 读取 exmip1 成功后，在 copy ctor 测试块
`lhs = imC2`（assignment operator）之后、`lhs.getNumRows()` 处崩溃：

```
Signal 5 (core dumped)
（exit 133，SIGTRAP；PC 稳定落在 ld-musl offset 0xb83a8 trap 路径）
```

## 根因

1. **soplex 3.1.1 的 SoPlex（SOPLEX_LEGACY 下 SoPlexLegacy）拷贝构造不可用**：
   `new soplex::SoPlex(*source.soplex_)` 生成的副本内部状态损坏，后续
   `soplex_->nRows()` 访问触发 trap。OsiSpx 自身 copy ctor 注释自述
   "Using the copy-constructor of SoPlex did not work, see #113"。
2. **OsiSpx 0.108.11 operator= 与自身 copy ctor 策略不一致**：copy ctor 用
   `*soplex_ = *source.soplex_`（赋值）规避拷贝构造，operator= 却仍用
   `soplex_ = new soplex::SoPlex(*source.soplex_)`（拷贝构造）。
3. **问题仅在运行期出现**：configure/编译均通过；RowCut/ColCut/Debugger 段
   不触发（不 deep-copy SoPlex），OsiSolverInterfaceUnitTest 的 copy-ctor 段
   触发。

## 方案（已落地补丁 0007）

修改 `OsiSpxSolverInterface::operator=`，与 copy ctor 完全一致：

```cpp
#if SOPLEX_VERSION >= 220
    spxout_ = new soplex::SPxOut;
    soplex_ = new soplex::SoPlex(*spxout_, soplex::SPxSolver::ENTER, soplex::SPxSolver::COLUMN);
#else
    soplex_ = new soplex::SoPlex(soplex::SPxSolver::ENTER, soplex::SPxSolver::COLUMN);
#endif
    *soplex_ = *source.soplex_;   // 赋值路径，弃用拷贝构造
```

- 补丁：`patches/0007-OsiSpx-operator-assignment-fix.patch`
  （diff -u 标准格式，patch -p1 dry-run/应用通过；conandata.yml 注册
  patch_type: bugfix）。

## 验证（R04 实测）

| 步骤 | 命令 | 退出码 | 结果 |
|---|---|---|---|
| 复现 | `./unitTest -mpsDir=../../Data/Sample -netlibDir=../../Data/Netlib -testOsiSolverInterface`（补丁前） | 133 | Signal 5 SIGTRAP，`lhs.getNumRows()`（soplex_->nRows()）；logs/osi-r04-repro-run.log |
| 崩溃点定位 | 代码级二分标记（-O0） | 133 | 精确到 `lhs=imC2` 之后、`lhs.getNumRows()` 处；osi-r04-diagmark4-run.log |
| 接口核对 | soplex.h / soplexlegacy.h / OsiSpx copy ctor 注释 | — | SOPLEX_LEGACY 下 `SoPlex ≡ SoPlexLegacy`；copy ctor 注释 #113 自证拷贝构造不可用 |
| 修复后 | 补丁 0007 应用，-O2 重建 `Osi/test/unitTest` 运行 | 0 | **1446 PASSED / 0 ERROR / 3 WARNING（预期内），"All tests completed successfully"**；osi-r04-verify-run.log |
| 归因 | — | — | **当前库 OsiSpx 适配可修**（非平台、非 soplex 二进制缺陷；上游 OsiSpx 自身策略即规避拷贝构造） |

## 适用边界 / 反例

- 适用：COIN-OR OsiSpx（及直接 `new SoPlex` 拷贝构造的同类 solver interface）
  在 soplex 3.1.x（SoPlexLegacy）下的运行期崩溃。
- 反例：copy ctor（赋值路径）本身不崩溃；RowCut/ColCut/Debugger 段不触发；
  上游 OsiSpx 新版统一 operator= 与 copy ctor 后问题消失。
- 与本 PR 中 DRAFT-osi-0.108.11-glpk5-lpx-api-removal 同属
  "依赖已发布 ≠ 接口可用" 教训的又一实例。

## 查重差异（七轴）

- exact_duplicate: 0（图谱 `grep -i soplex index.tsv` = 0 条 SoPlex 相关）
- causal_duplicate: 0
- trigger_overlap: 0（E198 为 Wdeprecated-copy 编译警告，因果不同）
- solution_overlap: 0
- combination_novelty: 1（SoPlexLegacy 拷贝构造损坏 × OsiSpx operator= 漏用赋值 × SIGTRAP 运行期崩溃）
- boundary_novelty: 1（COIN-OR solver interface × soplex legacy 边界）
- test_migration_novelty: 1（OsiSolverInterfaceUnitTest copy-ctor 段揭示，修复后段通过）

## 关系

- similar_to: [DRAFT-osi-0.108.11-glpk5-lpx-api-removal]
- caused_by: [soplex-3.1.1-so-plex-legacy-copy-ctor-broken]
- prerequisite_of: []
- conflicts_with: []