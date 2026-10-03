# DRAFT: 真机 shadow CI 隔离 job 的 KC 门禁挂在 `permission denied: bash`（PATH 缺 /data/service/hnp/bin 的门禁层表现）

## 基本信息

- 来源：sysrqd/17 真机 shadow CI r1（2026-10-01，job sysrqd-17-20261001）
- 阶段：shadow-ci / CI gate
- 严重度：2
- 同族根因：opencsg-1.8.2-shadow-ci-isolated-job-hnp-toolchain-path（该条是
  conan build() 阶段 cmake Error 127；本条是更早的 KC 门禁阶段 bash 被拒，
  失败面与检索词不同，故独立成条）

## 错误特征

```
ci/conan/build_and_test.sh:980: permission denied: bash
[fail] KC: knowledge check failed — blocking build
L0_RESULT=fail: knowledge_check failed
L1/L2/L4/L5_RESULT=skip: blocked_by_KC
```

注意：L0 已全 pass（R37/R38/R39 都过），包本身没有任何问题——挂在 KC 门禁
调用 `bash ci/scripts/knowledge_check.sh` 时找不到可执行的 bash。

## 根因分析

`ohos-prepare-isolated-conan-job.sh` 生成的 runner 环境只带
`$HOME/ohpc-ci-shadow/python-user/bin:$HOME/.local/bin` + 系统 PATH，而设备上
`/bin/bash`、`/usr/bin/bash` 均不存在（只有 `/bin/sh` 和 `zsh`）；GNU bash 5.3
实际位于 `/data/service/hnp/bin/bash`，该目录不在 runner PATH。
`build_and_test.sh` 的 KC 步骤显式 `bash <script>`，zsh 以 `permission denied`
形式报错并判 KC fail，连锁 block 全部下游门禁。

同批同设备的其它无关包同样挂在 KC（如 reniced r2），即可确认是环境级问题
而非当前包问题——多包同时挂同一门禁是快速判据。

## 推荐方案

**方法**：job-env-path-append-hnp-bin

修复 job 私有 `env.sh`（每个隔离 job 一份，不是 git 基础设施）：

```sh
echo 'export PATH=/data/service/hnp/bin:$PATH' >> "$JOB/env.sh"
# 验证
. "$JOB/env.sh" && command -v bash && bash --version | head -1
# 然后正常重跑
sh "$JOB/run-conan-heavy.sh"
```

注意：
- 不改 `ci/` 基础设施脚本（一库一 PR 边界）；env.sh 是 job 目录私有文件。
- conan profile 的 `[buildenv]` 已自带 hnp bin PATH，所以 conan create 本身
  能过——这也解释了为什么该问题只在 KC（build_and_test.sh 直接 `bash` 调用）
  暴露。
- 修复一次后同 job 后续轮次不再复发。

## 验证证据

sysrqd/17：r1 挂 KC（如上原文），env.sh 追加 hnp bin 后 r2 立即 KC pass
（KC1-KC5 全 OK）并一路跑到 conan create 成功、test_package 6/6 PASS。

---
Status: UNMATCHED
