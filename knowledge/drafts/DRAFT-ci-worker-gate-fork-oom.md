# DRAFT-ci-worker-gate-fork-oom：CI worker G0 门禁期 "fork failed: out of memory"

> Contributor: yanjiaxin | Status: pending-editor-review | Updated: 2026-09-20
> Source: PR #10825 knavalbattle/26.04.0 适配，CI 构建 #52699 @ OpenHarmonyPCDeveloper-CI-011

## 错误特征

```text
ci/conan/build_and_test.sh:116: fork failed: out of memory
program finished with exit code 1
elapsedTime=0.400069
```

- 发生在构建前门禁（G0 知识图谱完整性检查）第一步，一条 `ls | grep` 管道都无法 fork；
- 日志极短（48 行）、elapsedTime < 1s，任何包代码都还没开始编译；
- CI 自动诊断（ohpcd-robot）会把这类失败误归为 **"测试失败 / 上游官方测试未通过"**——这是误判。

## 根因

CI worker / 本地共享真机的系统内存或进程资源被并发任务耗尽，`fork()` 返回 ENOMEM。属于真机资源故障（同类：`can't fork` / `Errno 12`），与库代码、配方、测试无关（对应 E491 forbid_3：改包代码前必须先有设备资源证据）。

## 处理流程（三查一跑）

1. **查日志签名**：首行错误是 `fork failed: out of memory` + elapsedTime<1s + 门禁步骤即退出 → 资源故障特征；
2. **本地同命令复跑**：`CI_PACKAGES="archives/k/knavalbattle/26.04.0" CI_BRANCH="feat/knavalbattle-26.04.0" CI_PR_NUMBER="10825" zsh ci/conan/build_and_test.sh`，本地通过即证明包内容无问题；
3. **查资源**：确认机器 loadavg / /proc/meminfo / 并发 conan 任务已释放；
4. **重跑**：`/rebuild` 换 worker（集群多数 worker 内存充足，换机即绿的对照见 DRAFT-ci-lowmem-worker-link-oom-mitigation）。

全程**不改包代码、不删测试、不降优化档**（除非能证明是编译/链接期内存峰值——那属于 DRAFT-ci-lowmem-worker-link-oom-mitigation 的适用范围）。

## 验证

PR #10825 knavalbattle/26.04.0：
- CI 构建 #52699 失败（`build_and_test.sh:116: fork failed: out of memory`，elapsedTime=0.4s，G0 门禁第一步）；
- 本地以 CI 完全相同命令复跑：`G0_RESULT=pass`、`L0_RESULT=pass`、`L1_RESULT=pass`、`L5_RESULT=pass`、Pass rate 100.0% (1/1)；
- 结论：资源故障非代码问题，/rebuild 换 worker 后即可。

## 关联条目

- E491（swftools）：`forbid_3_pattern: retry.*(can't fork|Errno 12)`——资源耗尽必须先有设备资源证据再改包；
- DRAFT-ci-lowmem-worker-link-oom-mitigation：链接期（构建中）OOM 削峰，与本条"门禁期（构建前）fork OOM"互补。
