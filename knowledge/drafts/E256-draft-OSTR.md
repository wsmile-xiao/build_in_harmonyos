# E256 - Shadow CI 只看 git archive HEAD 快照，dirty worktree 不会自动进入验证

> **结构化数据**: [E256-draft-OSTR.kv](E256-draft-OSTR.kv)
> **类别**: ci/git/workflow | **严重度**: 🟡 | **阶段**: testing/ci

## 症状

本地工作区已经改好了包，但 shadow CI 远端还是报旧问题，或者直接提示没有可构建的包。

## 根因

shadow CI 不是在当前 dirty worktree 上直接跑，而是先把 `HEAD` 归档成干净快照。没提交的改动不会进入那个快照。

## 修复

1. 先提交目标包的最小快照。
2. 或者把目标包复制到一个新的干净仓库。
3. 再执行 shadow CI。

## 验证

- `git status --short` 先确认工作区状态
- `git archive HEAD` 里确实包含目标包目录

## 关系

- 这是工作流知识，不是包内功能知识。
