# DRAFT: shadow CI 经 ssh 启动 run-conan-heavy.sh 时 PATH 缺 hnp/bin——KC 段 git/bash 不可执行，伪装成 blocked_by_KC

- **日期**: 2026-09-29
- **来源**: mdns-reflector 0.0.1 适配（真机 shadow CI r1 轮）
- **平台**: HarmonyOS PC aarch64 / shadow CI 设备

## 现象

从工作机通过 ssh 启动隔离 job 的 `run-conan-heavy.sh`，几秒内 exit 1。
stdout 显示 G0/G0e 正常，随后：

```
[step] KC: Knowledge graph quality check...
ci/conan/build_and_test.sh:980: permission denied: bash
[fail] KC: knowledge check failed — blocking build
L0_RESULT=fail: knowledge_check failed
L1_RESULT=skip: blocked_by_KC
L2_RESULT=skip: blocked_by_KC
...
```

stderr 另有一行更早的 `ci/conan/build_and_test.sh:164: permission denied: git`。

**极具迷惑性**：输出看起来像知识图谱（KC）问题，容易误导向去查
knowledge/drafts 的草稿质量。

## 根因

`run-conan-heavy.sh` 内部 `env.sh` 用 `export PATH=<python-user/bin>:<.local/bin>:$PATH`
**继承 ssh 调用环境的 PATH**。非交互 ssh shell 的 PATH 不一定包含
`/data/service/hnp/bin`，而 `build_and_test.sh` 外层直接调用 `git`（G0e 段）和
`bash`（KC 段）——这两个工具只存在于 `/data/service/hnp/bin`（zsh 同理）。
PATH 缺失时 zsh 报 `permission denied: git/bash`，KC 段失败连带 L1–L5 全部
`skip: blocked_by_KC`。

Conan profile `[buildenv]` 的 `PATH=+(path)/data/service/hnp/bin` 只在 conan
命令内部生效，救不了 CI 脚本自身的 git/bash 调用。

## 解法（实测通过）

启动 runner 前在 **ssh 命令行**显式注入 PATH：

```bash
ssh <user>@<device> 'export PATH=/data/service/hnp/bin:$PATH; \
  sh ~/ohos-users/codex/<job>/run-conan-heavy.sh'
```

或按 E540 用 `ohos-test-runner.sh --path "$EXTRA_PATH"`。

诊断捷径：对同 job 的 run 目录比对
`ohos-test-runs/<run-id>/logs/env.txt` 中 PATH 是否含 `/data/service/hnp/bin`。

## 与现有条目的区别

- **E540**（zlib）：同为 runner PATH 缺 `/data/service/hnp/bin`，但症状在
  **配方构建期**（`make: inaccessible or not found`，exit 127），能走到 conan
  create；本条症状在 **CI 脚本外层**（git/bash），conan create 根本没启动，
  且以 `blocked_by_KC` 假象出现——排查方向完全不同（知识图谱 vs PATH）。
- **E518**：worker 上 git 因 libz.so 加载失败，是库依赖问题非 PATH。

## 复用要点

shadow CI 秒退 + 全线 `skip: blocked_by_KC` 时，**先查 run 目录 env.txt 的
PATH 有没有 /data/service/hnp/bin**，再看 stderr 有没有 `permission denied:
git/bash`，不要一头扎进知识图谱草稿排查。ssh 非交互 shell 的环境与历史成功
job（操作者当时带 hnp PATH）可能不同，"昨天同样的脚本能跑"不代表今天 ssh
裸调也能跑。
