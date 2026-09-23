# DRAFT-osi-0.108.11-l0i-platform-dead-branch — L0i 静态 AST 提取 tool_requires 不感知平台分支导致 registry_unreachable 假失败

- **知识 ID（草稿）**：DRAFT-osi-0.108.11-l0i-platform-dead-branch
- **路径**：Path B（知识库扩展）
- **来源事件**：osi 0.108.11 适配 W3（finish step 5/10）L0i 门禁失败
- **日期**：2026-09-16

## 问题

W3/build_and_test.sh 的 L0i 门禁（R36 依赖发布检查）报：

```
[error] registry unreachable for: msys2/cci.latest
conan stderr: Connecting to remote 'ohpcd' anonymously ERROR: error:system acceleration policy not enabled
[fail] L0i: Registry unreachable (infra error, not R36 violation): msys2/cci.latest
```

L0 判定 `registry_unreachable`，阻塞 finish W3，且提示方向是"修复 worker 网络"。

## 根因

1. L0i 用 `python3 ast.parse` + `ast.walk` 静态扫描 conanfile.py，收集所有
   `requires("x/y")` / `tool_requires("x/y")` / `build_requires("x/y")` 常量字符串，
   **不执行平台条件求值**：`if self.settings_build.os == "Windows"` 分支内才可达的
   `self.tool_requires("msys2/cci.latest")` 也被无条件提取并探测制品仓。
2. 复制自其他项目/上游模板的配方常携带 Windows 专用 `build_requirements()`
   （`self.win_bash = True` + `msys2/cci.latest`）。对 validate() 只允许
   Linux/OHOS 的目标包，这是永远不可达的死代码。
3. ohpcd（cnb.cool）对匿名探测**不存在的包**返回 "system acceleration policy
   not enabled"（E477 已记录该 CNB 特有文本），L0i 无法匹配
   `unable to find|does not exist|not found|404`，落入 registry_unreachable
   （网络/认证异常）分支——掩盖了"包不存在"的真实性质。

## 方案

1. 确认目标包 validate()/settings 只允许 Linux/OHOS（osi 即如此）。
2. 删除整个 Windows-only `build_requirements()` 死分支（win_bash + msys2）。
3. 重跑 finish W3：L0i 只探测真实依赖。

## 验证（osi 0.108.11 实测）

| 状态 | L0i 输出 |
|---|---|
| 删除死分支前 | `[error] registry unreachable for: msys2/cci.latest` → L0 fail |
| 删除死分支后 | `[ok] dependency in registry: coinutils/2.11.13` → L0/L0i/L0j/L0k/L0m 全绿 |

完整命令、退出码见适配 reports/w3-local-ci.log（osi 0.108.11）。

## 适用边界 / 反例

- **适用**：Linux/OHOS-only 目标包携带 Windows-only build_requirements 死分支。
- **反例**：包确实需要 Windows 构建（settings_build.os == "Windows" 可达）时不能删
  分支，应改条件 tool_requires 注入并确保 L0i 可解析，或依赖已发布 msys2 的仓；
  依赖真未发布（非死分支）时按 E477 核实发布，勿误判网络。

## 查重差异（相对既有条目）

| 轴 | 结果 |
|---|---|
| exact_duplicate | 0（无同条目） |
| causal_duplicate | 0（E477 因果为"依赖真未发布"，本候选为"死代码分支被静态提取"） |
| trigger_overlap | 1（同 L0i 探测 + 同 CNB acceleration policy 文本） |
| solution_overlap | 0（E477 建议核实发布；本候选建议删死分支） |
| combination_novelty | 1（L0i 静态 AST × 平台死分支 × CNB 假文本 组合） |
| boundary_novelty | 1（Linux/OHOS-only 配方边界） |
| test_migration_novelty | 0 |

关系：similar_to=[E477, DRAFT-6052-libnxml-0.18.5-ci-l0o-bare-dep-name-false-positive]；
caused_by=[]；prerequisite_of=[]；conflicts_with=[]。
