# DRAFT-21005: 本地 main 与 origin/main 分叉导致 W3 JC6 误拦——pr.diff 模拟 + 从 origin/main 重建分支

- **来源**：lwjson 1.9.0 适配（2026-10-04，PR 待定）
- **相邻条目**：DRAFT-boost-te（同一 junk_check 模式链，零提交/full 模式路径）

## 问题（一类）

多执行器共享主机上，本地 `main` 与 `origin/main` 深度分叉（本机实测：本地 214
个 local-only commits、远端 2478 个 remote-only commits，merge-base 退到很老的
点 7f702efc）。此时从本地 main 创建的新分支，其 junk_check **incremental 模式**
的三点 diff（`git diff origin/main...HEAD`）包含 **1330 个文件 / 107 个软件包**
的差异——全部是其他库的基线噪声，与本库无关。JC6 单软件原子性检查
（"本 PR 涉及 N 个软件包"）被污染拦截，W3 必失败（`w3_local_ci_failed`）。

这与 DRAFT-boost-te 的场景不同：那里是**零提交 → 三点 diff 为空 → 回退 full
模式 → JC5 杂项噪声**；这里是 **diff 非空但被其他库污染 → JC6 原子性误拦**。

## 方案（两条腿）

1. **本地 W3 用 pr.diff 忠实模拟真实 CI**：真实 CI（buildbot checkout-pr）由
   平台生成 PR 实际文件清单（pr.diff）并以 prdiff 模式检查，只含本库文件。
   本地生成同样的 pr.diff，junk_check 自动进入 prdiff 模式：

   ```bash
   git add -N archives/<l>/<sw>          # intent-to-add 使未跟踪文件可见
   git diff origin/main -- archives/<l>/<sw> > pr.diff   # 只含本库文件
   ```

2. **分支从 origin/main 重建**，保证远端 PR diff 干净（平台按
   merge-base..HEAD 计算；分叉基线会把污染带进 PR）：

   ```bash
   git branch -D feat/<sw>-<ver>
   git branch feat/<sw>-<ver> origin/main
   git worktree add <worktree> feat/<sw>-<ver>
   ```

   提交时只 `git add` 本库路径（submit 的定向 add 不会暂存缺失的十万+文件）。

## 验证（lwjson 1.9.0 实测）

- 从本地 main（3edb1a22）建分支：`git diff origin/main...HEAD` = 1330 文件
  （107 包），W3 JC6 拦截 "本 PR 涉及 107 个软件包"；
- 生成 pr.diff（仅 12 个 lwjson 文件）→ W3 build_and_test.sh 全绿
  （`检查模式: prdiff (12 个文件)`）；
- 分支从 origin/main（1262b4ac）重建后：`origin/main...HEAD` 三点 diff = 0，
  提交只含本库文件 → 远端 PR diff 干净。

## 适用边界

- 适用于共享主机上本地 main 与 origin/main 存在分叉的所有新分支；
- 本地 main 与 origin/main 一致时无此问题（三点 diff 天然干净）；
- 反例：分叉噪声 ≠ 本库缺陷，不要通过修改/删除其他库文件"修复"；
  **禁止 rebase/merge origin/main**（赛事交付禁改基线的零改写替代即重建分支）。

## 与既有知识的关系（七轴查重）

| 轴 | 结论 |
|----|------|
| exact_duplicate | 否 |
| causal_duplicate | 否（DRAFT-boost-te 触发=零提交 full 模式；本条=分叉基线 incremental 污染） |
| trigger_overlap | 是（同一 junk_check 模式链） |
| solution_overlap | 部分（都依赖 pr.diff/prdiff 模式；本条新增"分支从 origin/main 重建"） |
| combination_novelty | 有：分叉检测命令 + pr.diff 生成 + origin/main 重建组合 |
| boundary_novelty | 有：分叉 vs 零提交两条路径的判别（三点 diff 文件数与构成） |
| test_migration_novelty | 有：W3 模拟与真实 CI 的一致性论证（prdiff 模式同款判定） |

**决策**：new_draft（DRAFT-21005）——对 DRAFT-boost-te 部分覆盖，新增
"分叉基线污染 JC6 + 从 origin/main 重建"差异并已由 lwjson 真实日志验证。