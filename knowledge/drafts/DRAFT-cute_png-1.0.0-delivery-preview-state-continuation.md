# DRAFT-cute_png-1.0.0-delivery-preview-state-continuation — 人工批准的本地 delivery preview 必须保留同一 task_id 活动快照，不得以 completed/terminal 语义提交

> **Contributor**: pc1-71 | **Status**: DRAFT | **Updated**: 2026-08-31
> **Severity**: high | **Category**: ohos / ci / delivery / approval
> **Audience**: 处理 `delivery_approval_required: true` 任务（Path A/B/C 交付预览）的所有执行端

## Scope
当任务头声明 `delivery_approval_required: true` 时，本地生成的 delivery preview **不是最终业务结果**。
执行端必须以协议认可的 preview 状态 + 完整 preview 字段保存回报，才能保持同一 `task_id` 的活动快照
以供 `/approve` 批准与续跑。若把 preview 以 `completed`/`terminal` 语义提交，服务会生成终态 receipt、
清理活动快照，导致后续 `/approve` 返回 `409 stale_delivery_approval_rejected`（stale 拒绝）。

## 背景
- R05 实测：报告业务字段为 `status=delivery_preview_awaiting_approval`、`terminal=false`，但同 task_id
  的 result receipt 被服务记录为 `terminal=true`，且活动快照 `active-tasks/cute_png.json` 不存在，
  `POST /tasks/cute_png/approve` 返回 `409 stale_delivery_approval_rejected`。
- 这是"业务字段"与"receipt/快照"两层语义不一致造成的可复用问题样本，执行端不得自行修复（不得伪造
  receipt、直接改控制器状态或绕过批准）。

## 模式（步骤）
1. 读任务头，确认 `delivery_approval_required: true` 与 `delivery_approval_required` 存在。
2. 生成本地 delivery preview：标题（按路径 A/B/C 规定）、提交白名单、PR 草案、Issue 草案字段、
   本地门禁摘要、未执行远端动作。
3. 回报时保持协议认可的 preview 状态：`status=delivery_preview_awaiting_approval`（或服务接受的
   preview 状态枚举）、`terminal=false`、`delivery_approved=false`，并带完整 preview 字段。
4. 回报后轮询服务确认 `accepted: true` 且控制器置 `awaiting_user_approval`；保持同一 `task_id` 活动
   快照存活，等待用户批准。
5. 用户批准后（控制器记录 approval）才在本机执行任务明确授权的远端写入，并以同一 `task_id` 续跑回报。

## 最小可复用校验（一致性）
- `task_id`：回报与批准必须同一值，绝不得创建新 task_id。
- 活动快照：`active-tasks/<lib>.json` 存在 = 任务可续跑；不存在 = 已终态/已清理。
- preview 状态：业务字段必须为 preview 状态（非 completed/terminal）。
- preview 字段：`commit_preview` / `push_preview` / `pr_title` / `pr_body` / `file_whitelist` /
  `target_branch` / `local_gate_summary` 等完整字段。
- result receipt terminal 标记：终态 receipt 会清理活动快照 → 后续 `/approve` stale。
- approval 记录：批准前不执行远端写入；批准后同 task_id 续跑。
- 同 task_id 续跑能力：由活动快照存在性保证；快照被清理则无法续跑。

## 禁止
- 不得把 preview 以 completed/terminal 语义提交（伪造终态 receipt）。
- 不得直接修改控制器状态、active-task、approval 记录。
- 不得绕过批准执行远端写入。
- 不得创建新 task_id、新轮次或重发旧任务结果代替本任务续跑。

## 验证
- 回报后：`GET /tasks/<lib>` 返回同 task_id 且状态为 preview 相关（非 not_dispatched/completed）。
- `/approve`（用户批准后）不再返回 `409 stale_delivery_approval_rejected`。
- `active-tasks/<lib>.json` 在批准前存在，批准后按控制器流程变化。

## Source
- 事件：cute_png 1.0.0 R05 path_a_local_delivery_preview（pc1-71，2026-08-31）
- 证据：业务字段 status=delivery_preview_awaiting_approval / terminal=false；receipt terminal=true；
  active-tasks/cute_png.json 不存在；POST /tasks/cute_png/approve → 409 stale_delivery_approval_rejected。
- dedup_diff：与既有 DRAFT-jc-full-mode-git-index-isolation（基线噪声 W3 隔离/恢复）**不同主题**——
  本条是 delivery-preview 状态延续/活动快照/approval 生命周期，不涉及 git 索引隔离或 W3 重跑。
