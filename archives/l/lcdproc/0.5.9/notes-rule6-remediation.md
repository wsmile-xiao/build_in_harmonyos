chore(lcdproc): rule6 处置——把 960 commits 的陈旧基线 rebase 到最新 main

对应意见：平台评审 2026-09-30 16:02（comment id=192339451）rule6
         「无 AI 检视评论（未找到 gitcode-bot/atomgit-bot）」——本轮唯一 FAIL。

根因（取证，非推测）：
  1) atomgit-bot 的 7 次 /ai review 全部返回同一条终态：
     「准备检视工作副本（checkout）时超出单步时间上限，本次未执行检视」。
     失败点在 bot 的 checkout 准备阶段，尚未进入读码阶段。
  2) checkout 的输入是「本分支 tip」相对「main」的检出。本分支的 merge-base
     停在 401c1e75a9，落后 origin/main 共 960 个 commit：
         $ git rev-list --count $(git merge-base origin/main HEAD)..origin/main
         960
     960 个 commit 的漂移意味着 bot 需要在陈旧基线上准备工作副本，
     这正是仓内已记录的同类故障处方所指向的形态
     （knowledge/feedback：checkout-pr 失败 → 处方是 rebase 到最新 main）。
  3) 本 PR 自身 diff 不构成原因：20 文件 / 2548 行 / 全部为新增纯文本，
     最大单文件 43 KB（notes.md），远低于平台已知的「变更过大跳过」阈值。

改了什么：
  - git rebase origin/main（60ed502492），10 个 commit 线性重放，产出新 tip
    5574f48d83，落后 main 由 960 → 0。
  - **只改历史，不改内容**：rebase 前后 20 个文件的 blob 哈希逐一比对全等；
    根 .gitignore 的 blob 与 origin/main 相同（rule5 边界未破）。
  - 本 commit 仅新增本说明文件，配方 / 补丁 / test_package 零改动。

本地验证证据：
  $ git diff --shortstat origin/main...HEAD
    20 files changed, 2548 insertions(+)
  $ git diff --name-only origin/main...HEAD | grep -vcE '^(archives|knowledge)/'
    0
  $ git rev-list --count HEAD..origin/main
    0
