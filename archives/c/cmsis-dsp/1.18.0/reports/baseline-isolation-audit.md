# cmsis-dsp 1.18.0 — 基线隔离复验审计（baseline_isolation_audit）

task_id: cmsis-dsp-1.18.0-r01-pc7-5-20260920T123932Z · executor: pc7-5

## 背景
W3/finish 的本地 CI 模拟（build_and_test.sh → junk_check.sh）在 **full 模式（整仓扫描）** 下
仅命中当前库允许范围外、提交前已存在的其他库基线文件（main 基线中已跟踪的隐藏状态文件）。
按任务规则执行基线隔离复验：记录路径与隔离前 SHA-256 → 临时隔离 → 复跑受影响门禁 → 原样恢复并核对 SHA-256。

## 逐项审计记录

| 字段 | 值 |
|------|-----|
| path | archives/c/cloog/0.21.1/.build-closed |
| pre_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855（空文件） |
| isolation_command | `git rm --cached --quiet archives/c/cloog/0.21.1/.build-closed ...` |
| rerun_command | `bash ci/scripts/junk_check.sh .` |
| rerun_exit_code | 0（JC_RESULT=pass, Junk Files: 0） |
| restore_command | `git add -f archives/c/cloog/0.21.1/.build-closed ...`（-f 因 .gitignore 豁免） |
| post_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| pre==post | ✅ 一致 |

| path | archives/c/cloog/0.21.1/.staging-verified |
| pre_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| post_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| pre==post | ✅ 一致 |

| path | archives/k/kics/2.1.20/.staging-verified |
| pre_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| post_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| pre==post | ✅ 一致 |

- 隔离前/后 SHA-256 清单: /storage/Users/currentUser/tmp/cmsis-dsp-baseline-isolation/pre-sha256.txt 与 post-sha256.txt（diff 为空）
- 隔离后 junk_check 全量扫描: **0 杂项文件（JC_RESULT=pass）**，证明 W3 的唯一首错来自这些
  既有其他库基线文件，与当前库（cmsis-dsp）无关
- 当前库 diff/staged/PR 均未包含上述路径：本分支提交仅含 `archives/c/cmsis-dsp/**` 与知识库文件
  （`git status --porcelain -- archives/c/cloog/ archives/k/kics/` 为空）
- 未修改、未提交、未写入知识库/PR 上述基线文件（内容原样，SHA-256 前后一致）

## 结论
隔离复验通过 → 按任务规则继续当前库审计与交付，不构成外部阻塞停止条件。
