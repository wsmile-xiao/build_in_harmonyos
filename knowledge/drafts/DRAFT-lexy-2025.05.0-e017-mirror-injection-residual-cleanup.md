# DRAFT — E017 镜像注入残留清理：conandata URL 临时改写生成的非交付残留及其原子性排除

> 状态: 草稿（基于 lexy 2025.05.0 R02/R03 真实证据，待查重/提升）。
> 依据: SKILL §6 归档规范 + 铁律 R39（官方源）+ E017（ghfast 镜像）/ 铁律 R6/R10（不碰生成文件/临时文件）。

## 真实问题（场景）

在 lexy 2025.05.0 的 `conan-verify` / `finish`（W3）流程中，由于本环境 `github.com:443`
不可达，ohc-run 按 **E017 机制**在运行期间把 `conandata.yml` 的官方 sources URL 临时改写为
ghfast.top 镜像（并注入本地 `.build-cache/predl_cache/` 下载缓存），以保证 conan `get()`
能拉到源码。此镜像改写只是**传输通道**（conan 用归档 SHA-256 硬校验内容），但它在工作区
留下了多类**非交付残留**，若随 PR 混入即触发 CI JC1/JC5 junk 拦截：

- `archives/l/lexy/2025.05.0/conandata.yml.ghfast-bak`（镜像注入前的备份，内容=官方 URL 版）
- `archives/l/lexy/2025.05.0/conandata.yml.orig`（E017 回滚/再生成残留，url 字段为 gh-proxy 本地缓存路径）
- `archives/l/lexy/2025.05.0/.build-status.json.lock`（空锁文件）
- `.build-cache/predl_cache/0022786b_v2025.05.0.tar.gz`（下载缓存，非交付物）

R03 实测：`archives/l/lexy/2025.05.0/conandata.yml.ghfast-bak` 内容与官方 conandata.yml
逐字节一致（size=457）；`conandata.yml.orig` 的 `url` 字段被改写为
`gh-proxy.com/file://.../.build-cache/predl_cache/...tar.gz` 本地文件路径——这是 E017
注入后的形态，**绝不能作为交付源**。两者均被 `.gitignore`（`*.orig` / `*.ghfast-bak` 等）
覆盖，但 `git ls-files --others` 若不排除仍会出现在 untracked 审计里。

## 根因

1. **E017 镜像注入是运行期行为**：ohc-run 的 conan-verify/finish 在 `github.com` 不可达时，
   自动把官方 URL 临时改写为 ghfast 镜像（并回滚 conandata.yml），`get()` 靠 SHA-256 校验
   内容，源码与官方逐字节一致——但**回滚不彻底**会留下 `conandata.yml.ghfast-bak` /
   `conandata.yml.orig` 等备份/临时文件。
2. **本地文件系统形态 ≠ 交付形态**：`conandata.yml.orig` 里的 url 是
   `file:///.../.build-cache/...tar.gz` 或 `gh-proxy.com/file:///...`——仅在当前机器/当前
   worktree 可解析，任何提交/复用都会破坏 R39 官方源约束并让 CI 无法复现。
3. **junk 拦截按 git tracked/untracked 判断**：`ci/scripts/junk_check.sh` 的 JC1（运行时
   状态文件：`.bak|.orig|.rej|.ghfast-bak`、`.build-*`）与 JC5（archives 隐藏文件白名单）
   会对这些残留 fail；只有清理掉（或在白名单登记）才能通过 JC。

## 方案（精确清理 + 保持官方源）

1. **清理残留（rm 物理删除，不可 `git add`）**：
   - `rm -f archives/l/lexy/2025.05.0/conandata.yml.ghfast-bak`
   - `rm -f archives/l/lexy/2025.05.0/conandata.yml.orig`
   - `rm -f .build-status.json.lock`
   - `rm -rf .build-cache/`
   确认后 `git ls-files --others --exclude-standard | grep -v '^archives/l/lexy/'` 为空。
2. **保持 conandata.yml 官方形态**：`url` 必须回写为官方
   `https://github.com/foonathan/lexy/archive/refs/tags/v2025.05.0.tar.gz`，`sha256`
   `ae867846b890b7564d633cf28d39dfc4938fe7c54515126f720c1762de5eab30`（实测值），
   **不允许**任何 gh-proxy / file:// / ghfast 前缀。R39 铁律：URL 必须官方源，SHA-256 可硬校验。
3. **最终原子性审计**：staged=空、untracked 仅限当前库 `archives/l/lexy/` 允许文件、
   diff vs main 为空、无 commit/push/PR/远端写；三个无关基线文件不得进入 diff。
4. **复验**：清理后重跑 `finish lexy 2025.05.0 built`，W3 退出码 0、`.ci-result.json`
   exit_code=0、JC_RESULT=pass（Junk Files: 0），即 baseline_noise_exempted。

## R03 复验证据（真实观察）

- `python3 scripts/ohc-run.py finish lexy 2025.05.0 built --project-dir <wt>` → `EXIT_REASON=finish_success` `EXIT_CODE=0`。
- W3 本地 CI 模拟：`setup.sh` 通过、`build_and_test.sh` 通过、`JC_RESULT=pass` / `Junk Files: 0`；
  `.ci-result.json` 写入 `exit_code=0`、`integrity_hash=712e91b6a68a487c`、`log_sha256=a733618b...`。
- 隔离/恢复三基线文件（isa-l_crypto/middleclass/swift-corelibs-blocksruntime）前后
  SHA-256 与 HEAD blob 逐字节一致（d62412e1…/226348ef…/e3b0c442…），未删除/编辑/登记。

## 官方来源/sha256 不可被改写约束

- `conandata.yml` 的 `sources.url` 只能指向官方正式源（或权威镜像），且 `sha256` 必须为
  该 tarball 的实际哈希；镜像注入仅限**运行期传输通道**，结束后必须回滚为官方形态。
- 违反后果：CI 无法复现（URL 为本地 file:// 或 gh-proxy 包装）、R39 门禁 fail、PR 被拒。

## 适用边界

- 适用于：E017 镜像注入（ghfast.top / gh-proxy / gitcode 镜像）在 conan-verify/finish 中
  留下 `conandata.yml.*-bak` / `*.orig` / `.build-*.lock` / `.build-cache/` 残留的场景；
  也适用于任何需保证「运行期镜像≠交付源」的 C/C++ 库（同类先例 lexy 2025.05.0）。
- 不适用：若镜像改写后 conandata 的 sha256 被伪造/改动（非真实归档哈希），不属于残留清理
  范畴，属于伪造校验值，必须按铁律 R39/R6 停止并上报，不得清理后继续。
- 不适用：`conandata.yml` 本身就是用户/分析端授权的本地或镜像源（明确 R39 豁免）时，
  不强制回写官方 URL。

## 查重

搜索范围：`knowledge/drafts/` + `knowledge/graph/` + `knowledge/doc/`（grep
`e017|ghfast|镜像注入|mirror inject|gh-proxy`）。命中：E017 官方条目
（graph/E017.kv + doc/E017.md，主题=GitHub 下载慢/超时用 ghfast 加速）与多个草稿引用
E017（DRAFT-indicators…rewrite、DRAFT-highway-native-standalone-runner、E2149-draft-2301、
E321-draft-ASP1-proj-test-bootstrap-offline、E326-draft-4801、DRAFT-nymphrpc-sha256-multipath）。
**均未专门覆盖「E017 镜像注入残留的清理与原子性排除」**——本草稿为新增知识，无重复条目。
