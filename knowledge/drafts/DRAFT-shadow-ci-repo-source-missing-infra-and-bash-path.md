# shadow CI 隔离 job 双缺陷：repo-source 复制缺 ci/ 基础设施 + bash 不在预期 hnp 路径

> 草稿（DRAFT）。与同目录 `DRAFT-shadow-ci-repo-source-missing-infra-and-bash-path.kv` 成对。
> 实证来源：ndppd 0.2.6 真机 shadow CI r4/r5 轮（2026-09-29/30），设备无 git 场景。

## 现象

新库第一次用 `ohos-prepare-isolated-conan-job.sh --repo-source <旧job repo>` 建隔离 job 后，
`run-conan-heavy.sh` 秒退或门禁异常，出现**两种此前草稿未覆盖的失败**：

**失败 A（r4）**——CI 脚本层 127，日志 `ohos-test-runs/<run>/logs/stderr.log`：

```text
zsh: can't open input file: ci/conan/build_and_test.sh
runner.log: command='zsh' 'ci/conan/build_and_test.sh' 'archives/n/<库>/<版本>'
runner.log: end rc=127
```

**失败 B（r5）**——KC 门禁失败，stdout.log：

```text
[step] KC: Knowledge graph quality check...
ci/conan/build_and_test.sh:980: permission denied: bash
[fail] KC: knowledge check failed — blocking build
L0_RESULT=fail: knowledge_check failed
L1_RESULT=skip: blocked_by_KC
```

## 根因

两个**相互独立**的 job 初始化缺陷，都会在第一次用 `--repo-source` 复制的 job 上踩到：

**A：prepare 脚本复制 repo 时只带包相关目录**（archives/、knowledge/ 等少数顶层项），
不复制 `ci/`、`scripts/`、`templates/`、`references/`、`config/`、`docs/`。而
`run-conan-heavy.sh` 固定执行 `zsh ci/conan/build_and_test.sh`——文件不存在即 127。
**注意与既有草稿区分**：`DRAFT-shadow-ci-isolated-conanhome-missing-ohpcd-remote` 是
conan-home 缺 remote（依赖解析层），本条是 repo 本身缺 CI 脚本（执行层），失败点不同。

**B：设备上的 bash 不在 `/data/service/hnp/bin`，而在 `/data/service/hnp/bash.org/bash_5.3/bin`**
（实测 `ls /data/service/hnp/bin/bash` 不存在）。`build_and_test.sh:980` 的 KC 段用裸
`bash knowledge_check.sh` 调用；prepare 生成的 `env.sh` 默认 PATH
（`$HOME/ohpc-ci-shadow/python-user/bin:$HOME/.local/bin:$PATH`）不含 bash_5.3 路径。
**修正既有认知**：opencsg 草稿说"工具在 /data/service/hnp/bin"对 cmake/make/clang 成立，
对 **bash 不成立**——zsh 报 `permission denied: bash`（在 PATH 中搜到不可执行副本）而非
not found，容易误判为 HMDFS 执行位问题。

## 正确做法

job 创建后、跑 runner 前，**一次性补齐**（均在设备端，无需改基础设施脚本）：

```sh
# A: 从任一成功 job 的 repo 补齐缺失顶层目录（幂等，只补缺的）
SRC=$HOME/ohos-users/codex/<任一成功job>/repo/build_in_harmonyos
DST=$HOME/ohos-users/codex/<新job>/repo/build_in_harmonyos
cd "$SRC" && for f in * .[!.]*; do [ -e "$f" ] && [ ! -e "$DST/$f" ] && cp -a "$f" "$DST/"; done

# B: env.sh 的 PATH 前缀加 bash_5.3（对照 netselect 等成功 job 的 env.sh）
# HMDFS 上 sed -i 会失败，用 base64 整体重写：
echo <b64> | base64 -d > $HOME/ohos-users/codex/<新job>/env.sh
# 关键行：
# export PATH=/data/service/hnp/bash.org/bash_5.3/bin:$HOME/ohpc-ci-shadow/python-user/bin:$HOME/.local/bin:$PATH
```

## 快速诊断路径（排障顺序）

1. `ls -dt ~/ohos-test-runs/*<库名>*` 取最新 run 目录（**CI 真实输出在这里**，
   job 目录的 `logs/stdout.log` 一直是 0 字节，别盯着它等）
2. `cat <run>/logs/stderr.log` + `runner.log` → 127 且提示 build_and_test.sh → 缺陷 A
3. `grep -n "KC\|permission denied" <run>/logs/stdout.log` → KC/bash → 缺陷 B
4. 两者都修完再重跑 `nohup sh <job>/run-conan-heavy.sh`

## 验证

ndppd 0.2.6：补齐目录 + 修 PATH 后 r7 轮全门禁通过
（L0/L1/L4/L5 pass、L1e 负向验证确认、Build Summary 100%、exit 0）。
