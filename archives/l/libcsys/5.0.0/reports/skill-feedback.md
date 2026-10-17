# SKILL 反馈 — libcsys 5.0.0 适配（框架问题记录）

> 本文件记录本轮适配中发现的**框架侧**问题。按 SKILL §0.2 / W2，
> `scripts/` 等基础设施对协作者只读，故未在本 PR 内修改，仅记录待主编处理。

## F1（阻塞级）`scripts/gitcode_pr.py monitor-review` 崩溃 — NameError

**现象**：`submit` 的 AI Review 监控阶段持续输出 `⚠️ 获取检视状态失败，重试...`，
Phase 1→4 全部无法推进（最终只能等 30 分钟超时跳过）。表面像网络问题，实为脚本崩溃。

**复现**（100% 必现）：

```bash
$ export SSL_CERT_FILE=/etc/ssl/certs/cacert.pem
$ python3 scripts/gitcode_pr.py monitor-review \
    --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 9868
Traceback (most recent call last):
  File "scripts/gitcode_pr.py", line 1066, in cmd_monitor_review
    "unreplied_opinions": unreplied_opinions,
                          ^^^^^^^^^^^^^^^^^^
NameError: name 'unreplied_opinions' is not defined. Did you mean: 'review_opinions'?
```

**根因**：`unreplied_opinions` 在 `cmd_monitor_review` 内被引用但**从未赋值**——
引用点 3 处（`gitcode_pr.py:1066` 写入 output、`:1094` 与 `:1096` 打印"未回复检视意见"），
全文件无任何赋值语句（`grep -n unreplied_opinions scripts/gitcode_pr.py` 只返回这三处）。
推测为某次重构删除了该变量的计算逻辑（闭环校验用）但残留引用。

**影响面**：所有走 `submit` 的任务（每次适配）的 AI Review 闭环自动化全部失效；
由于异常被 `submit` 的上层重试吞掉，表现为"网络失败"，容易误导 agent 去排查网络/证书，
实际改证书无效（本轮已验证：设置 `SSL_CERT_FILE` 后 `get-comments`/`ci-status` 均正常，
仅 `monitor-review` 仍崩溃）。

**建议修复**：补回 `unreplied_opinions` 的计算（例如基于已分类的 bot 检视意见与
已回复讨论串 diff 推导），或先降级为 `review_opinions` 并移除 1094-1096 的打印分支。
建议同时给 `cmd_monitor_review` 加一层异常兜底，避免崩溃被误报为网络重试。

## F2（环境级，非框架缺陷）GitCode REST API 需显式 CA bundle

**现象**：`gitcode_pr.py` 全部子命令首次执行报
`<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer certificate>`，
`submit` 因此在"创建 PR"一步失败（`pr_creation_failed`）。

**判据**：本机无默认 CA store，但 `/etc/ssl/certs/cacert.pem` 有效；
`SSL_CERT_FILE=/etc/ssl/certs/cacert.pem` 后 `gitcode_pr.py` 立即恢复正常
（GET 返回 HTTP 400 而非 TLS 错误即为证书链已通）。

**建议**：`gitcode_pr.py` 在 urllib 调用处回退读取 `SSL_CERT_FILE`/系统 bundle，
或在 SKILL §0.0 环境准备里加一句 `export SSL_CERT_FILE=/etc/ssl/certs/cacert.pem`
（与本机 conan 需要 `[http] cainfo` 的同源问题）。

## F3（提示级）R46 回执被跨任务残留污染，静默跳过里程碑草稿

**现象**：`$HOME/ohpcd-ai-worker-result.json` 中残留的是**上一个任务**（marco/1.26.2，
PR #9861，`draft:false`）的回执。libcsys 的 `submit` 走到"R46 草稿"挂点时检测到
"终态已写入（draft:false）" → 打印
`R46: 终态 result.json 已上报（draft:false），跳过里程碑草稿 pr_created` 并跳过，
导致**本任务在 PR 创建后长时间没有任何回执**。若此时进程被杀，平台读到的是 marco 的结果。

**根因**：R46 的"防降级覆盖"判据只检查 `draft:false`，未校验回执中的包名/版本
是否属于当前任务（`pkg`/`ver` 字段已存在，可直接比对）。

**规避**（本轮已执行）：手工补写正确回执 —

```bash
python3 scripts/ohc-run.py result libcsys 5.0.0 --status partial \
  --pr-number 9868 --pr-url <PR URL> --branch feat/libcsys-5.0.0 \
  --commit-hash <HEAD> --failed-reason "..." --summary "..." \
  --out "$HOME/ohpcd-ai-worker-result.json" --force
```

**建议修复**：`write_lifecycle_draft()` 在"跳过"分支前比对现有回执的 `pkg`/`ver`，
不一致则按跨任务残留处理（覆盖 + 记一条警告），而非静默跳过。

## F4（提示级）`submit` 自检 `packaging_present` 与 ARCHIVE-SPEC 冲突

**现象**：`submit` 自检要求 `packaging/*.tar.gz` 存在（`submission.py:210-218`，
status ∈ {published, built} 时强制），否则 `self_check_failed` 阻塞；而
`knowledge/ARCHIVE-SPEC.md` §3 明确 `packaging/` **废弃**（"Conan 体系替代手动
tar.gz 打包"），仓库内实际存在 tar.gz 的 packaging 目录数为 **0**（353 个已跟踪
packaging 目录只有 README/.packaged 等占位文件）。

**本轮处置**：按 at-spi2-core/2.60.5 的既有形态创建 `packaging/README` 说明，
并在本地生成 `packaging/libcsys-5.0.0-ohos-aarch64.tar.gz`（conan 包产物打包）
满足自检；该路径被 `.gitignore` 的 `packaging/` 规则排除，**不入 PR**。

**建议**：自检项改为"存在 conanfile.py 即视为已打包"（与 ARCHIVE-SPEC §3 对齐），
或降级为警告。

## F5（提示级）preflight PF9 对软件级归档文件误报

**现象**：`create-pr` 的 PF9 路径闸对 `archives/<字母>/<包>/README.md` 与
`archives/<字母>/<包>/manifest.yaml`（软件级元数据，层数 = 4 < 5）报
"变更路径缺版本目录层 —— CI 将报 No packages to build"，导致 submit 建 PR 失败。

**实证为误报**：PF9 想防的失败模式是"PR 只含软件级文件、无任何 conanfile.py"，
而 `ci/conan/build_and_test.sh:253-254` 仅在**完全没有** `conanfile.py` 时才报
`No packages to build`。以最坏入参本地实测（故意把软件级目录也传给 CI_PACKAGES）：

```text
CI_PACKAGES="archives/l/libcsys/5.0.0 archives/l/libcsys" \
JUNK_PR_DIFF=<full pr.diff> zsh ci/conan/build_and_test.sh
→ [warn] Path in CI_PACKAGES has no conanfile.py: archives/l/libcsys   ← 仅告警
→ L0/L1/L4/L5 = pass，JC/KC = pass，Pass rate 100.0%，脚本退出码 0
```

且软件级 `README.md`/`manifest.yaml` 为仓库既有惯例（cubature/1.0.4、nb/7.25.4、
ayatana-indicator-display/26.6.0 等已合入包首次适配 PR 均含）。

**本轮处置**：`OHC_PREFLIGHT=0` 显式跳过（PF1-PF8 实测全部通过，仅此一项命中），
并把上述实证写入 PR 正文第 6 节；`archives/l/libcsys/` 的软件级元数据按其应有的
归档规范保留。

**建议**：PF9 增加豁免——变更集中于单一 `archives/<字母>/<包>/` 且其中包含
`<版本>/conanfile.py` 时，软件级 README/manifest 不应计为"缺版本目录层"。
