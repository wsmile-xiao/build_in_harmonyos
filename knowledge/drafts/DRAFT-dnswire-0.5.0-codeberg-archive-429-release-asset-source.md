# DRAFT-dnswire-0.5.0-codeberg-archive-429-release-asset-source

> Contributor: pc4-25 | Status: Draft | Updated: 2026-09-26
> Source: dnswire 0.5.0 R02 rework
> (task dnswire-0.5.0-r02-pc4-25-20260925T231839Z; R01 交付因 codeberg archive
> 端点 429 在远端 CI 失败而返工)
> 对应：knowledge/drafts/DRAFT-dnswire-0.5.0-codeberg-archive-429-release-asset-source.kv

## 现象

R01 交付的 conandata.yml 使用 `https://codeberg.org/DNS-OARC/dnswire/archive/v0.5.0.tar.gz`
（codeberg 动态 archive 端点）。远端 CI（conan-build-test #61289 及复跑）在 conan
source() 阶段连续失败：

```text
HTTP 429 Too Many Requests
（重试仍 429；本地交互式下载正常——限流主要针对 CI 自动化 IP/频率）
```

## 根因分析

codeberg 的 `/archive/<tag>.tar.gz` 是即时打包的动态端点，对自动化高频下载有
限流策略。而 dnswire 上游在 v0.5.0 release 页面公布了**官方 release asset**：
`https://www.dns-oarc.net/files/dnswire/dnswire-0.5.0.tar.gz`，并同时公布了
**官方 SHA-256**：`7db89f8118ea42b116fc211b05bc4253d105c86054c2dbce58f8ead80c8f3aad`。
稳定静态文件 + 官方摘要，是 CI 可复现下载的正确选择。

## 解决方案

1. conandata.yml 的 `sources.url` 改为官方 release asset URL，
   `sources.sha256` 改为官方公布值；
2. 重新下载并 `sha256sum` 实测核验一致（HTTP 200，SHA 精确匹配）；
3. 用同一 task_id 基于新 source 完整复跑：解压 → 补丁/pregen → configure/make →
   上游测试 → 鸿蒙专项 → test_package → 消费者验证 → conan-verify → finish/W2/W3；
4. 更新现有 PR（不重建）并触发一次 /rebuild。

```bash
curl -sSL -o dnswire-0.5.0.tar.gz https://www.dns-oarc.net/files/dnswire/dnswire-0.5.0.tar.gz
sha256sum dnswire-0.5.0.tar.gz
# 7db89f8118ea42b116fc211b05bc4253d105c86054c2dbce58f8ead80c8f3aad  dnswire-0.5.0.tar.gz
```

## 验证（R02 实测）

- 下载：HTTP 200；SHA-256 = `7db89f81…` 与官方公布值一致；
- conan create（新 URL）→ 通过；test_package PASSED；
- 上游 make check 6/6；鸿蒙专项 16/16；消费者 rc=0；
- conan-verify 通过；finish=published；W3 .ci-result.json exit_code=0；
- PR #12760 更新 + /rebuild 触发。

## 适用边界与反例

- **适用**：托管在 codeberg（或其他 git 托管动态 archive 端点）且上游发布官方
  release asset 的库；conandata 源 URL 应优先官方 release asset。
- **反例/边界**：
  - 上游只有动态 archive 而无 release asset 时，本方案不适用，须走
    E372（official-https-first-authority-http-fallback）/E335（官方 distfiles
    镜像）或退避重试，不得把 429 报成外部阻塞；
  - 429 偶发且重试可恢复时，先按 R41/R42 退避重试；连续多次仍 429 再切换源；
  - 切换源后必须重新核验 SHA-256（archive 端点与 release asset 摘要通常不同，
    本次实测 codeberg archive=9ea2f837… vs release asset=7db89f81…）。

## 四范围查重（七轴）

- **exact_duplicate**: false — 无条目描述 codeberg archive 429 → release asset 切换
- **causal_duplicate**: partial — E335（HTTP 418 反爬→官方 distfiles 镜像）、E372
  （curl/SSL 缺失→official-https-first）、E430（release asset 摘要与三方目录冲突→
  official-asset-digest-binding）同属"官方源选择/摘要绑定"因果族，但触发与对象不同
- **trigger_overlap**: true — 与 E335 共现"非 2xx 下载失败"触发面（418 vs 429）
- **solution_overlap**: partial — E372 official-https-first、E430 official-asset-digest-binding
  覆盖"选官方源+绑官方摘要"方案轴；本条目具体化到 codeberg archive→release asset 场景
- **combination_novelty**: true — "codeberg 动态 archive 端点 429 → 官方 release asset +
  官方公布 SHA-256"组合无既有条目
- **boundary_novelty**: true — 适用边界（codeberg+官方 asset）与反例（无 asset 时走镜像/重试）
  明确
- **test_migration_novelty**: true — conandata 源切换 + 同 task_id 全量复跑 + PR 更新的
  返工闭环可迁移至其他 source URL 返工任务

- **similar_to**: E335, E372, E430
- **caused_by**: —（上游/托管策略）
- **prerequisite_of**: —（暂无后续条目）
- **conflicts_with**: —（无冲突）

## 决策

- knowledge/doc：未命中（E271 单文件 asset 归档误判、E335 418 场景、E342 FetchContent、
  E372 工具链面、E430 三方目录摘要冲突——均非"codeberg archive 429"）
- knowledge/graph：未命中
- knowledge/drafts：未命中（DRAFT-ci-predl 为 CI 预下载 curl 缺失+镜像列表，不同根因）
- index.tsv：未命中
- **路径决定：B（new_draft）** — R02 source URL 修复过程中出现的真实可复用问题，
  已验证（HTTP 200+SHA 匹配+全门禁复跑）、可跨库复用、查重未命中且存在新增差异；
  建同 stem .kv/.md 草稿随 dnswire PR 交付。