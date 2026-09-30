# DRAFT-shadow-ci-kc-gate-bash-unreachable-misread-as-knowledge-failure — KC 门禁 bash 不可达伪装成"知识图谱失败"

> 草稿（DRAFT）。与同目录 `DRAFT-shadow-ci-kc-gate-bash-unreachable-misread-as-knowledge-failure.kv` 成对。

## 现象（极具误导性）

真机 shadow CI 在**任何包构建开始之前**就失败，输出形如：

```text
[step] KC: Knowledge graph quality check...
ci/conan/build_and_test.sh:980: permission denied: bash
[fail] KC: knowledge check failed — blocking build
L0_RESULT=fail: knowledge_check failed
L1_RESULT=skip: blocked_by_KC
L2_RESULT=skip: blocked_by_KC
L4_RESULT=skip: blocked_by_KC
L5_RESULT=skip: blocked_by_KC
```

stderr 里还常见一行 `build_and_test.sh:164: permission denied: git`（该调用被容错，不阻塞）。

表象是 `blocked_by_KC`，第一反应容易去改 `knowledge/` 草稿——**那是错路**。此时
G0/G0e/本包的 L0 结构检查（版本碰撞、commands.json、目录结构）其实都已通过。

## 根因

`build_and_test.sh` 的 KC 步骤（第 980 行附近）直接 `bash ci/scripts/knowledge_check.sh`
调用 `bash`；隔离 job 的 `env.sh` 生成的 PATH 只有
`$HOME/ohpc-ci-shadow/python-user/bin:$HOME/.local/bin:$PATH`，**不含
`/data/service/hnp/bin`**（bash 所在目录）。于是 KC 在门禁阶段就死掉，与你的
配方、补丁、知识草稿质量完全无关——是 job 环境问题。

为什么有的 job 不踩：`ohos-prepare-isolated-conan-job.sh` 生成 `env.sh` 时继承
**创建 job 那次 ssh 会话的 PATH**。若创建时登录 shell 恰好带 `/data/service/hnp/bin`
（例如前一个 job 的环境），新 job 就正常；非交互 ssh 默认 PATH 不含它，新 job 必踩。

## 排查顺序（看到 blocked_by_KC 先做这个）

1. `grep -E 'permission denied' <run>/logs/stderr.log` —— 有 `permission denied: bash`
   即命中本条，**不要动 knowledge/**。
2. 对比 env：`grep '^PATH' <run>/logs/env.txt` 与一个近期成功 job 的 env.txt，
   差集里有没有 `/data/service/hnp/bin`。
3. 设备上确认 bash 存在：`PATH=/data/service/hnp/bin:$PATH command -v bash`
   （注意 HMDFS 上 `ls -la /data/service/hnp/bin/bash` 可能报 Permission denied
   但执行正常，不要被 ls 误导——同 libsv 草稿的怪癖记录）。

## 解法（r2 实测生效）

给 job 的 `env.sh` 首行插入 hnp PATH 后重跑 runner（环境修复，不动配方、不动 CI 脚本）：

```sh
sed -i '1i export PATH=/data/service/hnp/bin:$PATH' \
  "$HOME/ohos-users/codex/<job>/env.sh"
sh "$HOME/ohos-users/codex/<job>/run-conan-heavy.sh"
```

等价做法（libsv 草稿）：启动 runner 时前缀 `PATH=/data/service/hnp/bin:$PATH`。
更省事的预防：**创建隔离 job 的那条 ssh 命令里就带
`PATH=/data/service/hnp/bin:$PATH`**，让 env.sh 生成时就含工具链目录。

## 与既有条目的差异（同根因、不同暴露点）

| 条目 | 暴露点 | 失败表象 |
|---|---|---|
| opencsg-1.8.2-shadow-ci-isolated-job-hnp-toolchain-path | build() 的 `cmake.configure()` | `cmake: inaccessible or not found`，Error 127 |
| libsv-1.2-shadow-ci-runner-toolchain-path | 同上（含 profile buildenv 未生效分析） | 同上 |
| **本条** | **KC 门禁阶段，早于一切包构建** | **`permission denied: bash` + `L0_RESULT=fail: knowledge_check failed` + 全链 blocked_by_KC** |

三条共用同一修复（PATH 注入），但诊断入口完全不同：前两条看 stdout 的 `RUN: cmake`；
本条看 stderr 的 `permission denied: bash`。误判成本也更高——KC 表象会把人引向
知识草稿 rather than 环境。

## 证据

starfetch 0.0.4（job `starfetch-0.0.4-20260929`，2026-09-29，设备 192.168.1.24）：

- r1：G0/G0e/本包 L0 全 pass 后 KC `permission denied: bash`，全链 blocked_by_KC，exit 1。
  env.txt 的 PATH 无 `/data/service/hnp/bin`；同期成功的 wordplay job env.txt 有。
- r2：仅在 env.sh 插入该 PATH 前缀，配方零改动，全绿：L0/L1/L1e/L2/L4/L5 pass、
  消费者测试 19/19、Build Summary 100%、exit 0。

## 禁止

- ❌ 不要因为 `blocked_by_KC` 去改/删知识草稿或 `ci/` 脚本——先查 stderr。
- ❌ 不要用 `--try-lock` 抢跑或绕过锁重跑（排队纪律不变）。
