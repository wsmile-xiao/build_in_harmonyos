# repo-source 快照缺 ci/ 目录：runner 秒败 exit 127，job 自身日志为空

> 草稿（DRAFT）。与同目录 `DRAFT-ntldd-0.2-shadow-ci-repo-source-integrity.kv` 成对。

## 现象

用 `ohos-prepare-isolated-conan-job.sh --repo-source <已有 job 的 repo>` 创建隔离 job
并启动 runner 后，几秒内失败：

- job 目录 `logs/` 下 stdout/stderr/exit-code **全空**（失败发生在 runner 外层逻辑里）；
- 真实错误在 `$HOME/ohos-test-runs/<run-id>/logs/stderr.log`：

```text
zsh: can't open input file: ci/conan/build_and_test.sh
exit-code.txt: 127
```

## 根因

设备无 git，job 的 repo 靠 `--repo-source` 复制既有 job 的仓库快照。**并非所有既有
job 的 repo 都完整**——实测同一设备上：

- `edlin-2.24-20260929/repo/build_in_harmonyos/` 只有 `archives/`，整个 `ci/` 缺失；
- `esekeyd-1.2.7-20260929/repo/build_in_harmonyos/` 完整（含 `ci/conan/build_and_test.sh`）。

runner 最终执行 `zsh ci/conan/build_and_test.sh <pkg>`，脚本路径不存在 → zsh 报
"can't open input file"，退出码 127。**这不是被测包的问题，也不进 L0 门禁**——
任何包借这个坏 repo 都会在同一位置死掉。

## 正确做法

创建 job 前先验证 repo-source 完整性（一条命令挑选可用的源）：

```sh
ls -t "$HOME/ohos-users/codex/" | head -8                       # 找近期 job
ls -d "$HOME/ohos-users/codex/"*/repo/build_in_harmonyos/ci/conan/build_and_test.sh \
  | tail -1                                                     # 取最新完整 repo
```

job 建好后、传包前再验一次：

```sh
ls "$CI_REPO_ROOT/ci/conan/build_and_test.sh" || echo "BAD repo-source, recreate job"
```

## 诊断路径（当 job logs 为空时）

job 自己的 `logs/` 为空 = 失败在 runner 外层。按顺序：

```sh
find "$HOME/ohos-test-runs" -maxdepth 1 -type d -name "*<库名>*"   # 找 run 目录
cat <run>/logs/stderr.log <run>/logs/exit-code.txt                  # 真实错误
```

## 查重与边界

- E518 是 worker 上 `git` 二进制缺 libz.so 导致 clone 失败（环境故障），本条是
  **无 git 设备上 repo 快照不完整**（数据问题），不同根因。
- opencsg 草稿（hnp-toolchain-path）是 PATH 缺工具，本条是脚本文件不存在。
- 修复零成本：换一个完整 repo-source 重建 job 即可，不要试图往坏 repo 里手工补
  `ci/`（容易漏目录，且下次重建 job 又回到坏源）。

## 证据

ntldd/0.2（2026-09-29）：

- r1 用 edlin job 作 repo-source：排队 5 秒后 exit 127，`zsh: can't open input
  file: ci/conan/build_and_test.sh`；
- 换 esekeyd job 作 repo-source 重建（r2 起）：runner 正常进入 G0e/G0/KC/L0 流程。
