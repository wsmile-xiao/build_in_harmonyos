# DRAFT: 隔离 shadow job 的 conan-home 缺 ohpcd remote（registry_unreachable）与 hnp 工具不入 PATH

- Status: UNMATCHED
- Category: shadow-ci / conan / environment
- Keywords: registry_unreachable, Remote 'ohpcd' doesn't exist, conan-home, remotes.json, ohos-prepare-isolated-conan-job, L0i, permission denied bash, PATH, hnp
- Related: E087, E098

## 现象（trickle-1.08 真机 r1/r2，2026-10-01）

用 `ohos-prepare-isolated-conan-job.sh` 新建的隔离 job 跑
`run-conan-heavy.sh`，两轮在 CI 早期失败：

1. **r1**：`L0i: Registry unreachable (infra error, not R36 violation)`，
   conan stderr 为 `ERROR: Remote 'ohpcd' doesn't exist`——配方全部依赖
   （automake/libevent/libtirpc/libtool/pkgconf）都被判"依赖不可达"，
   L1-L5 全部 `skip: blocked_by_L0`。这是**基础设施差异，不是依赖未发布**。
2. **r2**：remote 修好后卡在 `build_and_test.sh:980: permission denied:
   bash`——KC 检查用 `bash ci/scripts/knowledge_check.sh` 执行，而设备
   bash 位于 `/data/service/hnp/bin/bash`，runner 默认 PATH（/bin:/usr/bin:…
   :~/usr/local/bin）不含它。

## 根因

- job 创建脚本生成的 `conan-home/` 是全新 Conan 缓存：有默认
  remotes.json（仅 conancenter，甚至被禁用），**不带**本制品仓的 ohpcd
  remote；不同时期创建的 job 配置不一致（实测同一设备上 starfetch job
  也只有 conancenter，reniced job 则有 ohpcd）。
- runner（`ohos-test-runner.sh`）经 SSH 非登录 shell 启动，不加载 hnp
  环境；`/data/service/hnp/bin`（bash/gawk/make/autoconf/perl/as/ld 等）
  不在默认 PATH。

## 方案（job 层修复，不改仓库基础设施）

```sh
# 1) 从任一近期成功 job 复制 conan 配置（remote + 全局配置）
cp ~/ohos-users/codex/<good-job>/conan-home/remotes.json  <my-job>/conan-home/
cp ~/ohos-users/codex/<good-job>/conan-home/global.conf   <my-job>/conan-home/

# 2) 在 <my-job>/run-conan-heavy.sh 的 `. env.sh` 之后注入：
#    export PATH=/data/service/hnp/bin:$PATH
#    （HMDFS 上 sed 易碎，建议本地改好 base64 整体重写传输）
```

## 验证

r2 复制配置后 L0i 五个依赖全部 `[ok] dependency in registry`；r3 起
PATH 注入后 KC/JC 正常。后续 job（malint 等）同样会遇到，修复一次即
对该 job 持续生效。

## 复用面

所有新建隔离真机 job（每次 `ohos-prepare-isolated-conan-job.sh` 后）
第一次跑 runner 前都应做这两步；可按"找最近一次成功 job 复制 conan
配置"的口诀操作，避免每个包各花一轮真机才定位到。
