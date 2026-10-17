# DRAFT: worktree 本地 main 陈旧导致 create-pr PF1 单包闸误拦多包

## 基本信息
- **严重度**: 2（🟡 medium）
- **类别**: conan, ci, worktree, preflight, false-positive
- **作者**: calbee21
- **来源 PR**: !9640（mysql-client-8.0 8.0.46 适配）

## 错误特征
```
PF1 单包闸: 本 PR 改动涉及 11 个软件包目录，一个 PR 只允许一个包
```

## 根因分析
`scripts/ohc/preflight.py` 的 `run_preflight` 以 `args.target`（即 `main`）为 base 做 `main...HEAD` 三点 diff 收集变更文件。git worktree 共享主仓 refs 但多任务并行机器上本地 `main` 引用可能长期停在旧提交（其他任务只 fetch `origin/main` 不动本地 main）。此时三点 diff 的合并基取的是陈旧提交，main 上后来合入的其他包变更（muscle、rpm、openssl 等）全部计入本 PR 的"变更文件"，PF1 单包闸随即误拦。

## 推荐方案
**方法**: fast-forward-local-main-before-create-pr

**说明**: 在任务 worktree 内执行 `git fetch origin main:main`（本地 main 未偏离时直接 fast-forward 到 origin/main，无需 checkout），随后重跑 `create-pr`，PF1 即恢复单包判定。

**验证/命令**:
```
git rev-parse main origin/main   # 确认本地 main 落后
git fetch origin main:main       # 快进本地 main
python3 scripts/gitcode_pr.py create-pr ...  # 重试
```

## 证据链
- 首次 create-pr：PF1 报 11 个包目录（本分支仅 mysql-client-8.0 一个，其余 10 个为 main 后续合入的其他任务包）
- `git rev-parse main` = 9b49d7903 落后 origin/main a675263b9 共 33+ 提交
- `git fetch origin main:main` 后二次 create-pr PF1 通过，PR #9640 创建成功
- CI #44720、#44739 两轮均 PASSED

## 关键词
PF1, 单包闸, preflight, create-pr, worktree, 本地 main, 三点 diff, 多包误拦, fast-forward

---
*draft 状态，待人工审核提升为正式条目*
