# DRAFT-boost-di-1.3.2-gitcode-pf0-path-type：GitCode PR 客户端 PF0 preflight str repo_dir 导致 str/str TypeError

> Contributor: junshi_liu | Team: 兰州大学DSLab | Status: Draft | Updated: 2026-08-31
> Route: Path B（知识库扩展） | Source: boost-di 1.3.2 交付流程中发现的共享 GitCode PR 客户端缺陷

## 现象

在 boost-di 1.3.2 的授权 PR 交付流程中，使用当前 worktree 的 GitCode PR 客户端
（`scripts/gitcode_pr.py`）执行 `create-pr` 时，被 PF0 前置硬闸拦截，错误签名：

```text
unsupported operand type(s) for /: 'str' and 'str'
```

这是 PF0 环境闸（`preflight`）内部的类型错误，发生在任何 PR 写入之前。R15 中该 PR 创建
被拦截，**未创建、未更新任何 PR**；R15 与 R16 均未发生远端 API 写入、凭据访问、
commit、push、PR/Issue 动作。

## 根因

`scripts/gitcode_pr.py` 的 `cmd_create_pr` 调用 preflight 时，把 `_git_toplevel() or "."`
的**字符串**结果作为 `repo_dir` 传入 `run_preflight`：

```text
run_preflight(_git_toplevel() or ".", args.target, args.source)
```

而 `scripts/ohc/preflight.py` 的 `run_preflight` 内部以路径组合方式遍历包目录：

```text
pkg = repo_dir / d
```

`/` 运算符要求左操作数为 `pathlib.Path`。传入 `str` 时触发
`TypeError: unsupported operand type(s) for /: 'str' and 'str'`，被 preflight 的
fail-closed 逻辑捕获为 `PF0 环境闸` 拦截。

这是一个**共享 GitCode PR 客户端缺陷**，不是 boost-di 源码、配方、包或测试的失败；
它影响所有经 `gitcode_pr.py` 创建的 PR 流程。

## 解决方案（持久，属受控客户端）

持久修复属于 GitCode PR 客户端（`scripts/gitcode_pr.py` + `scripts/ohc/preflight.py`）：

1. 在客户端导入 `pathlib.Path`（缺失时）。
2. 把 `repo_dir` 以 `Path` 传入 `run_preflight`：

   ```text
   run_preflight(Path(_git_toplevel() or "."), args.target, args.source)
   ```

3. 增加一个**回归测试**，用 `Path` 类型的 `repo_dir` 练习 PF0（`run_preflight`），
   断言 PF1-PF4 正常执行且不抛 `str/str` TypeError。

`preflight` 绕过（`--no-preflight`）或伪造成功**均不是有效方案**；PR 交付只能建立在
真实 preflight 门闸与真实 readback 之上。

## 本地验证（R16，仅本地、无远端动作）

R16 在本地对上述最小临时修正做了定向无写验证：

- pre-change SHA-256：`e7d899d8dc4485abbf4ef1827d46736efc92ddd446e335192a46c6cb302ffbcb`
- 临时修复 SHA-256：`e96024218e5318e6a4a8bf25461a8e5fe81469c9899ea9df61077122b066ef32`
- 定向无写 PF0 验证退出码 0；`TypeError` 消失；PF1-PF4 在**未使用** `--no-preflight`
  的情况下真实执行。
- 验证结束后，`scripts/gitcode_pr.py` 已逐字节恢复为 pre-change 内容（恢复后 SHA 与
  pre-change 一致、零 diff）。R16 无远端 API、凭据访问、commit、push、PR/Issue 动作。

## 影响

- 直接阻断：凡经 `gitcode_pr.py` 的 `create-pr` 都会在 PF0 被 `str/str` TypeError 拦截，
  无法创建/更新 PR。
- 交付流程影响：R15 因此未能创建 PR；该缺陷为客户端侧，修复后需在另行获得显式远端
  授权的前提下重跑 create-pr + readback 才能闭合 PR 交付。
- 已推送代码不受影响：boost-di 的已推送 commit `79fa4119f6...` 与 12 个交付文件不变。

## 恢复

1. 由受控客户端维护者应用上述持久修复（Path 传参 + 回归测试）。
2. 在另行获得显式远端授权后，重跑 `create-pr` + `pr_readback`（验证 PR 号/URL/open/
   标题/body hash/base/head/head commit/精确文件清单）。
3. 只有真实 readback 证明每个字段后，PR 交付才可视为完成（本流程不预设交付成功）。

## 证据链（无秘密数据）

- R15 task：`boost-di-1.3.2-r15-repaired-executor-gitcode-pr-delivery-pc1-2-20260831T012938Z`
  - 证据日志：`$HOME/tmp/boost-di-r15-*.log`（ssh-state-audit、credential-use-audit、
    pr-materials-audit、pr-metadata-delivery、pr-readback、atomicity-audit）
  - 事实：PF0 拦截、错误签名、未创建 PR。
- R16 task：`boost-di-1.3.2-r16-temporary-gitcode-pf0-client-fix-pc1-2-20260831T015601Z`
  - 证据日志：`$HOME/tmp/boost-di-r16-*.log`（pf0-callsite-audit、temporary-client-fix、
    pf0-nonwrite-validation、client-recovery-audit、atomicity-audit）
  - 事实：最小临时修正验证（pre/temp/restored SHA 关系）、无写验证 exit 0、
    TypeError 消失、PF1-PF4 执行、客户端逐字节恢复。

本草稿区分了 R15 的历史受阻远端尝试（PR 未创建）与 R16 的仅本地修复验证（无远端动作）。
草稿不含任何凭据内容、认证配置、仓库密钥或远端动作声明。
