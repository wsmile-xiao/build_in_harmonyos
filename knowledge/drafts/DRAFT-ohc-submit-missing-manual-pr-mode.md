# draft-ohc-submit-missing-manual-pr-mode

## 症状 / 需求

`ohc-run.py submit <pkg> <ver>`（名义：「编译自检 / 提交」）的实现里，
门禁检查与 AI Review 全部通过后，会直接：

1. `git push origin <branch>`
2. `gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos`

也就是**自动创建真实 PR**。而任务约束经常是「只推工作分支 + 交付 PR 正文，
由人手动建 PR」。此时没有官方开关可用，只能：

- 手工 `git add/commit/push` + 自己抄 `_generate_pr_body()` 的表单，或
- monkeypatch 拦截（本任务用的临时脚本）：

```python
# $HOME/tmp/submit_<pkg>_manual_pr.py
import scripts.ohc.submission as submission
_real = submission.subprocess.run
def fake_run(cmd, *a, **kw):
    if isinstance(cmd, (list, tuple)) and any("gitcode_pr.py" in str(c) for c in cmd):
        return subprocess.CompletedProcess(cmd, 1, "", "manual-PR mode: create-pr intercepted")
    return _real(cmd, *a, **kw)
submission.subprocess.run = fake_run
```

拦截后 submit 仍会跑完全部门禁 + 自检 + `git commit` + `git push`，
只是不建 PR（handoff 记为 `pr_creation_failed`，附手动建 PR 提示）。

## 建议

给 `ohc-run.py submit` 增加 `--no-pr`（或 `--dry-run-pr`）：
完成门禁、生成 `reports/pr-body.md`、commit、push 之后跳过 `create-pr`，
并在 handoff 里以 `pr_creation_skipped`（而非 `pr_creation_failed`）落状态，
同时打印「PR 正文路径 + 建议标题 + 手动创建链接」。
这样既可满足「不得自动建 PR」的任务要求，也不需要用 monkeypatch 绕过，
避免拦截脚本自身的维护风险（例如内部函数改名、subprocess 调用形态变化）。

## 相关

- 触发实例：hamlib/4.7.1（2026-09-28，任务要求禁止自动建 PR）
- 拦截脚本：`$HOME/tmp/submit_hamlib_manual_pr.py`
- 涉及实现：`scripts/ohc/submission.py`（`cmd_submit` → `_generate_pr_body()` →
  `gitcode_pr.py create-pr`）；`~/.gitcode-token` 存在时若不拦截会真实建 PR
