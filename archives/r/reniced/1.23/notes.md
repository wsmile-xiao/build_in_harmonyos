# reniced 1.23 HarmonyOS adaptation notes

## Scope

- Package: `reniced/1.23`
- Upstream: `mmitch/reniced` tag `v1.23` (official GitHub tag archive preferred over the Debian `reniced_1.23.orig.tar.gz`, because only the tag archive contains `test/` and the Makefile)
- Source archive SHA256: `237f8d54e3885eb0a4fad881ece5b51fbeaf74c63191ad0c9f017c38598be390`
- Issue: 待补（per task instruction, issue number not yet assigned; 一库一 issue 需在 PR 前补齐）。

## W0 Dependency Check

- Conan 依赖：`perl/5.42.2.3`（主仓库已有配方目录；已由 dh-ros、ldap-git-backup、libnm 等近期包引用）
- 可选 Perl 模块：`BSD::Resource` —— 上游 POD 写了 `use BSD::Resource;`，但实际代码在 `get_prio_process()` 中用 `eval { require BSD::Resource; }` 加载，失败时回退 `PRIO_PROCESS = 0`（Linux 上 0 恰为正确值）。**无需为本包单独适配该模块**。
- 运行时外部命令：
  - `ps`（必需，`ps H -o lwp,comm --user <uid>` 或 root 下 `ps H -eo lwp,comm`）—— OHOS toybox ps 语法支持需真机验证；上游测试与 test_package 均用 mock ps，不阻塞本机适配。
  - `ionice`（可选，仅 IO 优先级规则需要）。
- 缺失依赖拆分：不需要。
- W0 结论：依赖数量 1（perl）；已满足；缺失 0；阻塞点无。

## Source And Build Analysis

- 纯 Perl 单文件应用（485 行，GPL-2.0-or-later），无编译，无 Makefile 构建步骤（Makefile 仅用于上游打 tarball/生成 manpage）。
- 归档内容：`reniced`、`reniced.conf`、`COPYRIGHT`、`HISTORY`、`README.md`、`Makefile`、`.github/workflows`、`test/`。
- 上游测试：`test/run-tests`（bash）循环执行 3 个 `.test`（bash）并与 `.expected` 做 `diff -Narup`：
  - `show-help.test`：`reniced -h` 输出与版本占位比对。
  - `normal-run.test`：mock ps + `reniced -n test.conf`（no-op 模式）。
  - `verbose-run.test`：同上但 `-n -v`，并用 sed 归一化 UID 和 BSD::Resource 来源。
  - 全部测试不需要 root、不需要真实进程表、不需要 setpriority 权限 —— no-op 模式只打印 "would ..." 行。
- 测试审计结论：3/3 上游测试默认可在 HarmonyOS PC 执行，前提是有 `bash`；`sed`/`grep`/`diff` 用法简单，toybox 兼容性风险低（E010 关联但此处仅用基础参数）。

## Packaging

- `bin/reniced`（OHOS 重写 shebang 为 `/data/service/hnp/bin/perl`，参照 mysqltuner 先例）
- `share/reniced/reniced.conf`（示例配置）
- `share/doc/reniced/README.md`、`HISTORY`
- `licenses/COPYRIGHT`
- `runenv_info` 暴露 perl 与包 `bin/` 的 PATH。

## Recipe Behavior

- `build()`：校验归档文件 → `perl -c reniced` → 有 bash 时从临时目录副本执行上游 3 个 no-op 测试。OHOS 适配（均不改 Conan source 目录中的上游文件）：
  - 上游 `.test`/mock `ps` 的 shebang `/bin/bash` 在设备不存在（bash 在 `/data/service/hnp/bin`，E037/E049）→ 副本中改用显式解释器调用。
  - 设备禁止 exec 任何新建文件（无论分区与权限，SELinux 标签策略；HMDFS conan-cache 与 app-data 分区实测均 `Permission denied`）→ `../reniced` 与 mock ps 一律经显式 perl 调用；上游 `run-tests` 的 `diff -Narup` 被 toybox 拒绝 `-p`（E010）→ 期望输出用 Python 逐行比对（等价上游 diff）。
- 打包脚本含**一行适配注入**：`open PS, '-|', $cmdline` 前插入 `RENICED_PS_CMD` 环境变量覆盖（默认不设置时行为与上游完全一致）。目的：设备无法 exec 新建 mock ps 文件，消费者测试经显式 perl 运行 mock。PR 补丁说明中明确记录。
- `test_package/test_reniced.py`：布局断言 + 打包文件含 RENICED_PS_CMD 覆盖点 + `reniced -h`（原样打包文件）+ 设 `RENICED_PS_CMD` 后对打包脚本做 no-op 运行，逐行断言与上游 `normal-run.expected` 完全一致。

## Shadow CI 迭代记录

| 项 | r1 (job) | r2 | r3 | r4 | r5–r7 | r8（最终） |
|---|---|---|---|---|---|---|
| job | reniced-1.23-20261001 | r2 | r3 | r4 | r5/r6/r7 | r8 |
| exit | 1 | 1 | 1 | 1 | 1 | **0** |
| 门禁 | L0 fail: registry_unreachable | KC fail: permission denied bash | KC/L0 pass；build fail: /bin/bash shebang | KC/L0 pass；perl -c OK；build fail: HMDFS exec 拒 | show-help 逐步通过；normal-run 因重定向缺失/mock 参数串丢弃失败 | **G0/KC/JC/L0/L1/L4/L5 全 pass，L2 非阻塞 skip** |
| 根因 | 隔离 CONAN_HOME 未跑 ci/conan/setup.sh，ohpcd remote 缺失 | job PATH 缺 /data/service/hnp/bin（bash/zsh/perl 所在） | 上游 .test shebang /bin/bash + diff -Narup 的 -p 被 toybox 拒 | conan-cache(HMDFS) 及任意新建文件 exec 被 SELinux 拒（bad interpreter/Permission denied） | run-tests wrapper 的 `> test-output.actual` 重定向遗漏；RENICED_PS_CMD 需为命令前缀拼接（保留原 ps 参数串） | — |
| 解法 | setup.sh 初始化 remote（mysqltuner 草稿先例） | retry 脚本 PATH 前置 hnp/bin | 副本显式 bash 执行 + Python 比对 | 全链路显式解释器调用 + RENICED_PS_CMD 一行注入 | 补重定向；mock 改前缀拼接并 shift 首参 ps | — |

## True-Device Shadow CI Final Result (r8, 2026-10-01)

- exit code：0；Pass rate：100%（1/1）
- G0_RESULT=pass；KC_RESULT=pass；JC_RESULT=pass
- L0_RESULT=pass（perl/5.42.2.3 在 ohpcd registry；reniced/1.23 首次发布无版本冲突；commands.json 有效；目录结构合规）
- 上游测试：3/3 通过（show-help、normal-run、verbose-run，no-op 模式 + mock ps，构建副本显式解释器执行，输出与上游 .expected 逐行一致）
- `perl -c reniced`：syntax OK
- test_package：5 组断言全部 PASS（布局 / RENICED_PS_CMD 覆盖点 / -h Usage / -h 版本 1.23 / 打包脚本 no-op 输出与上游期望一致）
- L1e 破坏性反向验证：pass（"test genuinely depends on reniced"）
- L4_RESULT=pass（no patches）
- L5_RESULT=pass（bin/ has content）
- L2_RESULT=skip（non-blocking）：CI 直接 exec `<pkg>/bin/reniced --help` 失败，与 mysqltuner 先例一致——设备禁止 exec HMDFS Conan cache 上的新建脚本；解释器显式执行已在 test_package 中验证（`perl <pkg>/bin/reniced -h` exit 0）。

## Verification (local, Windows host)

- 源码归档下载 + SHA256 复核：通过（GitHub v1.23 tag archive；网络不稳，ghfast/gh-proxy 前缀亦失败，最终经直连成功，配方保留 4 级 fallback URL 列表）。
- 归档结构检查：通过，含 reniced/reniced.conf/COPYRIGHT/HISTORY/README.md/test/。
- Debian `reniced_1.23.orig.tar.gz`（SHA256 `f71c10cc0192a7c7877b8d249c24099e34efc513153d92714d899ca35cc5f172`）无 test/，仅作对照，不用于配方。
- Python 语法检查：通过（compile() 文本检查，本机无 conan/perl）。
- YAML 结构检查：通过。
- `git diff --check`：通过。
- Conan create / perl -c / 上游 bash 套件：本机未执行（无 conan、perl、bash），如实记录，待真机 shadow CI。

## Next True-Device/Shadow CI Commands

```sh
CI_PACKAGES="archives/r/reniced/1.23" zsh ci/conan/build_and_test.sh
```

Suggested isolated job shape:

```sh
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job reniced-1.23-$(date +%Y%m%d-%H%M%S) \
  --package archives/r/reniced/1.23 \
  --repo-source <existing-repo>

sh "$HOME/ohos-users/codex/<job>/run-conan-heavy.sh"
```

If running manually without the helper-generated runner (read-only /tmp workaround per mysqltuner draft):

```sh
export CONAN_HOME="$HOME/ohos-users/codex/<job>/conan-home"
export TMPDIR="$HOME/ohos-users/codex/<job>/tmp"
export TMPPREFIX="$TMPDIR/zsh"
export CI_PACKAGES="archives/r/reniced/1.23"
zsh -c 'mktemp() { command mktemp -p "$TMPDIR" "$@"; }; . ./ci/conan/setup.sh'
zsh -c 'mktemp() { command mktemp -p "$TMPDIR" "$@"; }; . ./ci/conan/build_and_test.sh'
```

Device-side focus points:

1. `reniced/1.23` 是否已被制品仓占用（若占用需按 R37 递增为 1.23.1 并同步目录/配方/分支名）。
2. 设备是否提供 `bash` 与 `diff -Narup` 支持，决定上游套件能否在 build() 直接跑。
3. L2 直接执行：hmdfs 上脚本 exec 权限受限（E087/mysqltuner 先例），预期需解释器显式执行 `perl <pkg>/bin/reniced -h`。
