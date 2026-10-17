# DRAFT-ohos-conan-source-host-unreachable-byte-identical-mirror：
# Conan source() 官方源码 host 在 CI 沙箱内 TCP 不可达 → 字节一致镜像托管

> Contributor: siril-1.2.3 适配 | Status: Draft | Updated: 2026-09-05
> Source: archives/s/siril/1.2.3（PR #8366，gitlab.com ConnectTimeout 实测）

## 现象

siril/1.2.3 的 `conandata.yml` `sources.url` 指向官方 gitlab.com 归档
`https://gitlab.com/free-astro/siril/-/archive/1.2.3/siril-1.2.3.tar.bz2`。
权威 CI（PR #8366 多轮）在 `source()` 阶段（conanfile.py `get()` 第 94 行）
反复失败：

```text
WARN: network: Error downloading file https://gitlab.com/free-astro/siril/-/archive/1.2.3/siril-1.2.3.tar.bz2:
'HTTPSConnectionPool(host='gitlab.com', port=443): Max retries exceeded with url:
... (Caused by ConnectTimeoutError(...'Connection to gitlab.com timed out. (connect timeout=30)'))'
ERROR: siril/1.2.3: Error in source() method, line 94
ConanException: Error downloading file ...
[fail] siril/1.2.3 — conan create failed
```

关键对比：**同一时刻，本机 curl 该 URL 返回 HTTP 200（3.46s）**，本地重建
`siril_rebuild7.log` 全绿（36/36 依赖、test_package PASS）；只有 CI 沙箱
连 gitlab.com 超时。即"本机可达 ≠ CI 可达"。

## 根因分析

- CI 沙箱网络策略使 **gitlab.com 整机不可达**：TCP 连接 30s 超时
  （`ConnectTimeoutError`），不是 HTTP 418 反爬、不是 404、不是 sha256 错误。
- `ci/conan/build_and_test.sh` 的镜像回退（约 L1019 起的通用镜像映射）与
  pre-download（L1164 起，`get_mirror_list`）**共用同一份受限白名单**：
  github.com（gh-proxy）、GNU（清华/中科大/阿里）、GNOME、
  `gitlab.gnome.org`、SourceForge、kernel.org、boost、curl.se、xorg。
  **gitlab.com 不在白名单内** → `sources.url` 不被改写为镜像、pre-download
  也不兜底（其 `mirrors = [url]` 仍指向 gitlab.com），conan 直连超时即败。
- 全库 57 个配方以 gitlab.com 为 `conandata.yml` 源（`grep -rl
  "url:.*gitlab\.com" archives --include=conandata.yml` 计数），均有同类风险。
- 这是与"编译/配方/补丁"无关的**纯网络可达性**问题：本地重建证明配方本身正确。

## 解决方案

1. **字节一致镜像托管到 CI 可达平台**（siril 采用）：

   把官方归档（位级相同）托管到被既有 published 配方证明 CI 可达的平台
   （atomgit.com、gitee.com、gitcode.com），用其 `api/v5 repos/.../raw`
   端点 + **固定 commit sha 经 `?ref=` 锚定**，`conandata.yml` 仅替换
   `url` 的 host，**sha256 与文件名不变**。

   ```yaml
   # 官方 gitlab 归档（sha256 47dcaa34bbe3...e63833）字节一致镜像：
   url: "https://atomgit.com/api/v5/repos/SnowTT/build_in_harmonyos/raw/mirror%2Fsiril%2F1.2.3%2Fsiril-1.2.3.tar.bz2?ref=baeda7622422bb9ff82ea9c94ba5fb971140f6c8"
   sha256: "47dcaa34bbe32f9f866e07233519d5ccc8ce487beb6932c050cf4ff505e63833"
   ```

   合规依据：R37 L0j 明确"**换 host 但文件名+sha 相同**"视为源身份未变更
   （位级相同，语义等价），不触发版本冲突；托管分支与 PR 分支分离，
   PR diff 只含 URL 一行 + 注释，无大文件入 diff。

2. **托管要点（避坑）**：
   - 不要用 atomgit 的 `/raw/<ref>/<path>` 直链——实测返回 3576 字节 SPA
     页面而非文件；须用 `api/v5/repos/<owner>/<repo>/raw/<path>?ref=<sha>`。
   - 托管分支用**专用分支**（如 `mirror/siril-1.2.3`）并记录 pinned sha，
     不要放进 PR 分支（否则 4.6MB 二进制入 diff）。
   - 必须复核：新 URL 下载后 `sha256sum` 与 conandata 完全一致（三方一致）。

## 验证证据

- 镜像 URL `https://atomgit.com/api/v5/repos/SnowTT/build_in_harmonyos/raw/...`
  实测 HTTP 200、size=4615997、sha256=`47dcaa34bbe32f9f866e07233519d5ccc8ce487beb6932c050cf4ff505e63833`，
  与官方归档 `sha256sum` **逐字节一致**。
- 本地 `conan create` 侧的全部依赖/构建/测试已由 `siril_rebuild7.log` 证明
  通过（镜像字节与官方完全相同，编译行为不变）。
- CI 复验：PR #8366 重新触发后应在 source() 阶段直接成功进入编译（待用户
  `/rebuild` 触发确认）。

## 查重（B1 去重证据摘要）

- 检索词：`gitlab.com` / `ConnectTimeout` / `connect timeout` /
  `Max retries exceeded` / `Error downloading file` / `byte-identical` /
  `字节一致` / `host-only` / `换 host`（`knowledge/` 全目录 grep：
  index.tsv + graph/*.kv + drafts/*.kv）。
- 结果：以"**CI 沙箱 host 整机不可达 + 字节一致镜像托管 + host-only 换源
  sha256 不变**"为问题层的条目 **0 命中**；命中均为同族相邻条目（见下表）。
- 结论：**同族可申报**，问题层（root cause 与修复路径）为新增，需下表定位差异。

## 相关既有条目差异化定位表

| 条目 | 问题层（根因/机制） | 与本草稿差异 |
|---|---|---|
| E017 | GitHub 下载慢/超时 → ghfast/gitee/gitcode 代理加速 | 面向 **github.com 下载慢**（非不可达），用代理改写；不涉及 CI 白名单未覆盖、不涉及字节一致镜像托管与 R37 身份判定 |
| E299 | Conan source() 下载失败的分层诊断框架（传输/HTTP/哈希） | 是**分类框架**，不含"host 在 CI 沙箱整机 TCP 不可达 + 镜像白名单未覆盖 → 字节一致镜像托管"的具体解法；其 forbid 禁止的是未锚定的个人 blob/滚动分支（与本草稿"固定 commit sha 锚定"一致不冲突） |
| E335 | gitlab.alpinelinux.org 418 反爬 → 改用 Alpine 官方 distfiles 镜像 | 根因是 **HTTP 418 反爬**（服务端有响应、拒绝 UA）；改官方 distfiles 源，无字节一致性/R37 考量 |
| E347 | gitlab.com / gitlab.alpinelinux.org 418 反爬 → conan download cache 预置（curl 预下载） | 根因是 **418 反爬**；预置本地 cache 的前提是**本机/CI 能连通 gitlab**——host 整机 TCP 不可达时 curl 同样失败，此方案失效（siril 即此情形） |
| E372 | 最小 worker 无 curl/SSL → 官方 HTTPS 第一 + 权威 HTTP 字节一致镜像第二（fallback） | 面向**无 curl/SSL 的 worker**，保留官方 URL 第一、镜像仅作 fallback；本问题是官方 host 在 CI 不可达，**URL 必须整体替换**，且镜像须托管在 CI 可达平台、以固定 sha 锚定 |

- 新增价值：确立"官方源码 host 在 CI 沙箱内整机不可达且镜像白名单未覆盖"
  这一独立问题层的识别（ConnectTimeout vs 418 vs 哈希错误）与修复范式
  （字节一致镜像托管 + api/v5 raw 固定 sha + host-only 换源 sha256 不变），
  与 E017/E299/E335/E347/E372 互补，构成源码下载故障图谱的独立节点。

## 禁止做法

- 不要用 atomgit `/raw/` 直链（返回 SPA 页面）或未锚定 `?ref=` 的滚动分支
  raw 直链——内容会漂移，破坏 sha256 可信度与 R39 合规。
- 不要为"host 不可达"改用 gitee 再生归档（位级不同、需重算 sha256、属真实
  源变更）；仅当目标项目有 gitee mirrors 且版本未发布时可作 fallback（
  rocksdb 先例），且必须本地复验构建。
- 不要仅凭"本机 curl 200"判定源可用——CI 沙箱网络策略与本地不同，须以
  CI 实测为准。
