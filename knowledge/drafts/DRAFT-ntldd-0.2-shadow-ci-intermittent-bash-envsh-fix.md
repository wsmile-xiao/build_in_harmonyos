# CI 公共脚本里的裸 `bash` 间歇性 Permission denied：在 job 的 env.sh 前插 hnp bin

> 草稿（DRAFT）。与同目录 `DRAFT-ntldd-0.2-shadow-ci-intermittent-bash-envsh-fix.kv` 成对。
> 是 opencsg 草稿（runner 调用层 `--path` 注入）的姊妹条：本条故障发生在
> **CI 公共脚本内部**、且是**间歇性**的，修法落在 **job 自己的 env.sh**。

## 现象

真机 shadow CI 走到 KC（知识图谱质量检查）步骤时失败：

```text
[step] KC: Knowledge graph quality check...
ci/conan/build_and_test.sh:980: permission denied: bash
[fail] KC: knowledge check failed — blocking build
L0_RESULT=fail: knowledge_check failed
L1_RESULT=skip: blocked_by_KC
```

特征：

- 失败点是 `ci/conan/build_and_test.sh` 内部的裸 `bash <script>` 调用（该行为
  无法通过自己的包配方控制）；
- **间歇性**：同一设备、同一 env.sh、几分钟前另一个 job 的 KC 正常通过
  （`[ok] KC: knowledge check passed`），几分钟后自己的 job 失败；
- 诊断证据：登录会话里 `command -v bash` 无输出、`ls /usr/bin/bash` 报
  `Permission denied`（zsh 报 permission denied 而非 not found，说明解析到了
  `/usr/bin/bash` 但 exec 被拒）；而 `/data/service/hnp/bin/bash` 始终可执行。

## 根因

设备上裸 `bash` 解析到 `/usr/bin/bash`，其可访问性受设备侧安全状态影响而
间歇波动（本例中兄弟 job 前后行为不一致，非配方或包问题）。CI 公共脚本不可
修改，但 **runner 的 env 由 job 的 `env.sh` 提供**——在那一层把 hnp 的 bash
顶到 PATH 最前面，即可让脚本里所有裸 `bash` 调用稳定解析到可用副本。

## 修复（只动自己 job 的文件，零越权）

```sh
echo "export PATH=/data/service/hnp/bin:\$PATH" >> \
  "$HOME/ohos-users/codex/<job>/env.sh"
# 之后正常重跑 run-conan-heavy.sh
```

注意转义 `\$PATH`（追加到文件里应保留字面 `$PATH`）。test_package 里的
`CONFIG_SHELL` 默认值 `/data/service/hnp/bin/bash` 也因此受益，无需再改。

## 与相关条目的边界

| 条目 | 故障层 | 差异 |
|---|---|---|
| opencsg hnp-toolchain-path | 包构建里 `cmake: inaccessible`（Error 127） | 工具从来不在 PATH；修在 runner 调用层 `--path` |
| E346/E326 | make 的 `SHELL=/bin/sh` | 固定路径写死，非间歇 |
| 本条 | CI 公共脚本内部裸 `bash`，间歇性 | 修在 job 的 `env.sh`，不改公共脚本、不改配方 |

先决判据：`ls /usr/bin/bash` 报 Permission denied、`/data/service/hnp/bin/bash -c
echo ok` 正常 → 用本条；若是 `not found` 且构建期缺 cmake/make → 用 opencsg 条。

## 证据

ntldd/0.2（2026-09-29，真机）：

- r3a：KC 步骤 `permission denied: bash`，exit 1（同设备 esekeyd job 4 分钟前
  KC 通过，env 完全相同）；
- 在 r3 job 的 env.sh 前插 hnp bin 后重跑：KC、L0、构建、L1e、L2、L5 全部通过，
  最终 exit 0（run ...-103931-45230）。
