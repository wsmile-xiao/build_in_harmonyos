# DRAFT-osi-0.108.11-glpk5-lpx-api-removal — GLPK >= 4.53 移除 lpx_* 传统 API（R03 边界修正 / R05 恢复路径实证 / R06 制品落地），COIN-OR OsiGlpk 接口无法编译

- **知识 ID（草稿）**：DRAFT-osi-0.108.11-glpk5-lpx-api-removal
- **路径**：Path B（知识库扩展）
- **来源事件**：osi 0.108.11 R02 `--with-glpk`（GLPK 5.0）、R03 `--with-glpk`
  （GLPK 4.65，边界修正）、R05 `--with-glpk` + oldapi/lpx 兼容层（恢复路径实证）、
  R06 `--with-glpk`（glpk/4.65.1 制品含 liblpx）+ `--with-soplex` 双段（制品落地）
- **日期**：2026-09-16（R02），2026-09-18（R03 边界修正 / R05 实证），2026-09-19（R06 制品落地）

## 问题

对 osi 0.108.11 配置 `--with-glpk` 启用开源求解器 GLPK 时，configure 成功
（GLPK 探测 yes，`COIN_HAS_GLPK=1`，`osi-glpk.pc` 生成），但 make 编译
`Osi/src/OsiGlpk/OsiGlpkSolverInterface.cpp` 失败：

```
OsiGlpkSolverInterface.cpp:172:13: error: use of undeclared identifier 'lpx_simplex'
OsiGlpkSolverInterface.cpp:182:16: error: use of undeclared identifier 'LPX_E_SING'
OsiGlpkSolverInterface.cpp:183:5: error: use of undeclared identifier 'lpx_adv_basis'
...
```

全文件共 189 处 `lpx_*` 调用全部未声明，make exit 2。R03 用 GLPK 4.65 复测，
首错 `OsiGlpkSolverInterface.cpp:241:8: error: use of undeclared identifier
'LPX_E_NODFS'`（20 个错误），现象完全一致。

## 根因

1. **GLPK 破坏性版本变更（边界修正）**：GLPK 自 4.45-4.52 时代即移除传统
   `lpx_*` API（GLPK NEWS："All obsolete GLPK API routines (prefixed with lpx)
   were removed"），自 4.52+ 仅以 `examples/oldapi/lpx.{h,c}` 独立可选兼容层
   提供（需单独编译链接，主库/主头文件不含）。因此 **GLPK >= 4.53 的官方
   `glpk.h` 中均无任何 `lpx_*` 符号**（4.65 与 5.0 实测一致；R02 草稿原写
   ">= 5.0"且反例"4.65 可编译"，经 R03 实测否定）。
2. **Osi 0.108.11 的 OsiGlpk 未迁移**：该接口仍完整基于 lpx_* API 编写，
   无 `glp_*` 新 API 版本分支。
3. **configure 探测不足**：`--with-glpk` 只校验头文件与链接可行性，不校验
   接口符号族 → 配置成功、编译失败。核心教训：**依赖已发布（R36 通过）≠
   API 兼容**。

## 方案

1. 引入 GLPK 前先核对版本兼容：Osi 0.108.11 OsiGlpk 需要携带 lpx_* API 的
   GLPK 制品（GLPK >= 4.53 官方制品均无；唯一路径是发布时把
   examples/oldapi/lpx.c 编译进库或提供独立 liblpx）。
2. 版本不兼容时保留 `--without-glpk`，测试入口如实计为未实例化并给出恢复条件，
   不得把 configure 成功当作可实例化。
3. 恢复条件（二选一，R05 已实证 a 路径可行）：
   a) 【R05 实证：已验证可行】制品仓发布保留 lpx_* 兼容层的 GLPK 版本——
      把官方 examples/oldapi/lpx.{h,c} 编译为 liblpx（111 个 lpx_* 符号）与
      libglpk 一起发布；下游 OsiGlpk 需内建处理手段：
      `-include lpx.h`（预包含 lpx_* 声明，OsiGlpk 只 include glpk.h）、
      `-DGLP_PROB_DEFINED`（跳过 OsiGlpk 头对 glp_prob 的回退 typedef）、
      `-Wl,--gc-sections`（丢弃未引用的 standalone lpx_main→glp_main）。
      R05 实测：静态覆盖 100%（集合差缺失 = 0），链接/运行 OsiGlpk 段成功，
      unitTest 1501 PASSED / 0 ERROR / exit 0。
   b) 等待/贡献上游将 OsiGlpk 迁移至 glp_* 新 API。

## 验证

osi 0.108.11 R02 实测（GLPK 5.0）：

| 步骤 | 命令（节选） | 退出码 | 结果 |
|---|---|---|---|
| 制品可用性 | `conan download glpk/5.0 -r=ohpcd` | 0 | 已发布，OHOS arm64 clang15 二进制存在（requires gmp/6.3.0） |
| configure | `./configure ... --with-glpk-incdir=<glpk>/include --with-glpk-lib="-L<glpk>/lib -lglpk"` | 0 | COIN_HAS_GLPK=1，osi-glpk.pc 生成 |
| make | `make -C Osi` | 2 | 首错 `use of undeclared identifier 'lpx_simplex'`（189 处 lpx_*） |

证据：`reports/osi-glpk-attempt-configure.log`（SHA-256 d89df059...）、
`reports/osi-glpk-attempt-make.log`（SHA-256 a7f96c33...）。

osi 0.108.11 R03 边界修正实测（GLPK 4.65，R02 反例否定）：

| 步骤 | 命令（节选） | 退出码 | 结果 |
|---|---|---|---|
| 官方源码核验 | `curl -fsSL https://ftp.gnu.org/gnu/glpk/glpk-4.65.tar.gz` | 0 | SHA-256 4281e29b628864dfe48d393a7bedd781e5b475387c20d8b0158f329994721a10（与 ohpcd conandata 一致） |
| 头文件符号 | `grep -c "lpx_" src/glpk.h`（官方解包） | 1 | 0（1175 行，无任何 lpx_* 符号）；ohpcd 发布包 glpk.h 逐字节一致亦为 0 |
| 库符号 | `nm -D <glpk>/lib/libglpk.so.40 \| grep " T lpx_"` | 1 | 0（glp_simplex 存在，lpx_* 无导出） |
| configure | `./configure ... --with-glpk-incdir=<glpk/4.65>/include --with-glpk-lib="-L<glpk/4.65>/lib -lglpk"` | 0 | COIN_HAS_GLPK=1 |
| make | `make -C Osi -j4` | 2 | 首错 `LPX_E_NODFS` 与 `lpx_simplex` undeclared（20 错误） |

证据：`reports/osi-r03-configure.log`、`reports/osi-r03-make.log`。

osi 0.108.11 R05 恢复路径实证（GLPK 4.65 + oldapi/lpx 兼容层）：

| 步骤 | 命令（节选） | 退出码 | 结果 |
|---|---|---|---|
| 兼容层编译 | `clang -c -O2 -fPIC -ffunction-sections -I<glpk>/include -I oldapi lpx.c` | 0 | liblpx.a（111 个 lpx_* 符号） |
| 静态覆盖比对 | 提取 OsiGlpk 非注释 `lpx_*` 57 + `LPX_*` 43，对照 oldapi 112+90 符号集合差 | 0 | **缺失 = 0（100% 覆盖）**；注释伪引用 lpx_add_xxx/LPX_E_OPT 已排除 |
| configure | `--with-glpk-incdir=<glpk>/include --with-glpk-lib="-L<glpk>/lib -lglpk -L<oldapi> -llpx"` | 0 | COIN_HAS_GLPK=1 |
| 构建 OsiGlpk | `make -C Osi CPPFLAGS="-include lpx.h -DGLP_PROB_DEFINED"` | 0 | libOsiGlpk.a 构建成功 |
| 构建 unitTest | `make -C Osi/test unitTest ... LDFLAGS="-Wl,--gc-sections"` | 0 | 链接成功 |
| 运行 | `./unitTest -mpsDir=Data/Sample -netlibDir=Data/Netlib -testOsiSolverInterface` | 0 | **1501 PASSED / 0 ERROR / 1 WARNING（预期内）/ "All tests completed successfully"**（含 OsiGlpk 段全量 + OsiPresolve + Netlib） |

证据：`reports/glpk-oldapi-coverage-r05.log`（SHA-256 fe953113...）、
`reports/osi-r05-glpk-unittest-run.log`（SHA-256 59aaedf8...）。

osi 0.108.11 R06 制品落地（glpk/4.65.1 已发布 + liblpx + soplex 双段）：

| 步骤 | 命令（节选） | 退出码 | 结果 |
|---|---|---|---|
| 依赖核验 | `conan list/download glpk/4.65.1 -r=ohpcd` | 0 | 已发布（OHOS 制品含 lpx.h sha256 5fe3a003...、liblpx.a 111 个 lpx_* 符号） |
| configure | `--with-glpk-incdir=<glpk/4.65.1>/include --with-glpk-lib="-L<glpk>/lib -lglpk -llpx" --with-soplex ...` | 0 | COIN_HAS_GLPK=1 + COIN_HAS_SOPLEX=1 |
| make Osi | `make -C Osi ... -include lpx.h -DGLP_PROB_DEFINED` | 0 | libOsiGlpk.a + libOsiSpx.a 构建成功 |
| make unitTest | `make -C Osi/test unitTest ... -Wl,--gc-sections` | 0 | 链接成功 |
| 运行 | `./unitTest -mpsDir=Data/Sample -netlibDir=Data/Netlib -testOsiSolverInterface` | 0 | **2763 PASSED / 0 ERROR / 4 WARNING（预期内）/ "All tests completed successfully"**（OsiGlpk + OsiSpx 双段 + OsiPresolve×2 + Netlib） |

证据：`reports/osi-r06-configure.log`、`osi-r06-make.log`、`osi-r06-build-unittest.log`、
`reports/osi-r06-fullsuite-run.log`（SHA-256 640ad303...）。与 glpk 侧
`DRAFT-glpk-4.65.1-lpx-compat-layer` 构成上下游衔接（glpk 制品交付 ↔
osi 段消费验证闭环）。

## 适用边界 / 反例（R03 修正 + R05 实证 + R06 落地）

- 适用：全部 COIN-OR 系 solver interface（OsiGlpk 同款接口亦存在于 Clp/Cbc 系）
  在 **GLPK >= 4.53**（含 4.65、5.0）下 `--with-glpk` 的场景。
- 反例（修正）：R02 原反例"GLPK 4.x 仍保留 lpx_*（如 4.65）"经 R03 实测
  **不成立**——仅 GLPK 4.45-4.52 区间版本保留 lpx_*（制品仓未发布）。
- 恢复路径（R05 实证）：携带 examples/oldapi 兼容层的制品**可实例化**——
  静态覆盖 100% + 实际链接/运行通过（须内建 `-include lpx.h` /
  `-DGLP_PROB_DEFINED` / `-Wl,--gc-sections` 处理手段）。上游将 OsiGlpk
  迁移至 glp_* 后新版本 Osi 不受影响。
- 与 E062/E065（gnulib 头文件/宏缺失的 undeclared identifier）trigger 文本
  重叠但因果不同（本候选是上游库移除 API，非本地宏缺失）。

## 查重差异（七轴）

- exact_duplicate: 0（图谱 `grep -i glpk index.tsv` = 0 条；无 oldapi/lpx 兼容层条目）
- causal_duplicate: 0
- trigger_overlap: 1（trigger 同 R02/R03：lpx_* undeclared / GLPK 无 lpx_*；
  与 E062/E065 文本重叠但 causal 不同）
- solution_overlap: 1（方案同"发布 lpx 兼容层"，R05 补实测验证 + 发布处理手段）
- combination_novelty: 1（GLPK >= 4.53 lpx_* 移除 × COIN-OR solver interface ×
  制品可用但 API 不兼容；R03 补官方源码 SHA 取证；R05 补 oldapi 兼容层
  100% 覆盖 + 实际链接/运行通过实证）
- boundary_novelty: 1（COIN-OR 系 solver interface 边界；R03 将边界从 5.0
  修正为 4.53+；R05 将恢复条件从理论升级为已验证可执行）
- test_migration_novelty: 1（测试实例化尝试揭示依赖 API 断裂；R03 反例否定
  证据；R05 unitTest 含 OsiGlpk 段从 uninstantiated → passed 实跑 1501 断言）

## 关系

- similar_to: [E062, E065]
- caused_by: []
- prerequisite_of: [glpk-with-lpx-compat-layer-publication]
- conflicts_with: []
