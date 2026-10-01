# rule6 会被「用空提交换 SHA 触发 CI」反向击穿

## 症状

内容全绿、CI 也绿，平台评审却判 **VERDICT=FAIL**，13 条规则里只有 rule6 红：

| 规则 | 结果 | 说明 |
|------|------|------|
| rule4 验证结果 | ✅ PASS | 编译通过 + 通过率达标 |
| rule7 CI 校验状态 | ✅ PASS | CI 状态: 通过 |
| rule12 鸿蒙特有测试 | ✅ PASS | N=2 ≥ 1 且含完整消费者用例 |
| **rule6 AI 检视 P0/P1** | **❌ FAIL** | **最新提交晚于最新 AI 检视 → 检视未覆盖最新提交** |

FAIL 原因串里没有任何一条指向代码：

```
规则 6: 最新提交 2026-09-30T08:23:04+08:00 晚于最新 AI 检视
        2026-09-30T07:44:14+08:00 → 检视未覆盖最新提交,提交后须再次 AI 检视
```

注意 rule6 的判定要点写的是「AI 检视评论里 P0/P1 级别问题数=0」——**P0/P1 本来就是 0**。
它红的是时序：评审拿「HEAD 提交时间」和「最近一次 AI 检视时间」比大小。

## 根因：为了绕开坏 worker 造的 `--allow-empty`，恰好推进了 HEAD 时间戳

先看 HEAD 是什么：

```
$ git show --stat 92341408b1
ci(rearm): layer-A worker retry #2 -- obtain fresh SHA for CI-038 re-queue

本 commit 不改动任何文件。唯一目的是产生新 SHA 以便平台重新排队。

$ git diff --stat 2308fc6cc4 92341408
(空 —— HEAD 与父提交内容逐字节一致)

$ git log -1 --format=%ci HEAD
2026-09-30 08:23:04 +0800
```

起因是一次真实的坏 worker 故障，与仓库内容无关：

```
$ git clone --depth 1 …/build_in_harmonyos.git . --progress
error: cannot fork() for git-remote-https
program finished with exit code 128
elapsedTime=0.379635
```

`cannot fork()` 是 worker 侧进程资源耗尽（另见 `zsh:1: fork failed: out of memory`，
`elapsedTime=0.046s`）。因为失败发生在 `git-clone` 步骤——**还没 checkout 到本 MR 的任何文件**——
所以「换了 SHA 也没用」的直觉是对的，但**用的手段是错的**。

关键的三个事实叠在一起才构成这个坑：

1. **CI 是评论触发型。** push 本身不触发 CI，必须评论 `/rebuild`。
   → 所以「造新 SHA 让平台重新排队」这个前提从一开始就是假的。
2. **AI 检视不会因 push 自动重跑。** 必须评论 `/ai review`。
   → 推新提交只会让 HEAD 时间戳跑到检视时间之后。
3. **`--allow-empty` 一样会写提交时间。** 它不改变 tree，但改变 HEAD 的提交时刻。

于是这个本意是「绕过坏 worker」的动作，**唯一确定的后果**是把 rule6 击穿。

## 为什么它还没能达成目的

`git diff 2308fc6cc4 92341408` 为空，说明新 SHA 的内容与父提交逐字节一致。
既然内容没变，就没有任何东西需要重新校验——而 CI 也不会因为 SHA 变了就跑。
换句话说这个提交**两头落空**：既没触发 CI（push 不触发），
又把 rule6 弄红了（时间戳推进了）。

## 正确处置

**不要用提交去调门禁。** CI 和 AI 检视的触发器都是评论，与提交无关：

1. 把所有内容修订——代码、配方、`notes.md`、`audit-result.json`、MR 描述——
   **一次性做完并提交**；
2. push 之后**不再追加任何提交**。事后补一份文档同样会改变 HEAD 时间戳并重新击穿
   rule6（`feedback/SKILL_FEEDBACK_29e8b891.md` 记的就是这个流程教训）；
3. 评论 `/ai review` 等检视出结论；
4. 评论 `/rebuild` 等 CI。

## 诊断口径

看到 rule6 FAIL 且 P0/P1 = 0 时，按这三步判断，不要去改产品代码：

```bash
git log -1 --format='%h %ci %s' HEAD        # HEAD 时间 vs 检视时间
git show --stat HEAD                        # 空输出 + 主题含 rearm/CI ⇒ 空提交
git diff --stat HEAD~1 HEAD                 # 为空 ⇒ 内容未变 ⇒ 无需重新校验
```

本仓已有多次同类记录（`SKILL_FEEDBACK_0ffe7ce1.md`、`SKILL_FEEDBACK_29e8b891.md`、
`archives/k/kio-kwallet/6.28.0/notes.md` 的 R-3），处置方式一致：
**重新触发 `/ai review` + `/rebuild`，不动代码。**

## 顺带一条：坏 worker 的识别

`cannot fork()` / `fork failed: out of memory` 且 `elapsedTime < 1s`、
失败步骤是 `git-clone` 或 `cleanup`（即尚未开始编译任何源码）——
这是 worker 容量故障的签名，**与配方无关**。处置是 `/rebuild` 换 worker 重试，
不要改配方。