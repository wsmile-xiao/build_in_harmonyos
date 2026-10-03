# DRAFT: 隔离 shadow-CI job 的 CONAN_HOME 未初始化 → ohpcd remote 缺失 → L0i registry_unreachable

- Status: UNMATCHED
- 来源: reniced 1.23 shadow CI r1（2026-10-01，job reniced-1.23-20261001）
- 关联: E477（registry 探测误判为网络异常，但那是 CNB 加速策略问题）、mysqltuner notes 先例

## 错误特征

用 `ohos-prepare-isolated-conan-job.sh` 创建隔离 job 后，直接跑
`run-conan-heavy.sh`（即 `ohos-test-runner.sh -- zsh ci/conan/build_and_test.sh <pkg>`）：

```
[step] L0i: Checking dependency availability in registry (R36)...
        [retry] registry probe 1/3 failed for perl/5.42.2.3 (transitive?), retrying...
        [error] registry unreachable for: perl/5.42.2.3
        conan stderr: ERROR: Remote 'ohpcd' doesn't exist
[fail] L0i: Registry unreachable (infra error, not R36 violation)
L0_RESULT=fail: gate failed: registry_unreachable
```

依赖明明已发布在 ohpcd，却被判 `registry_unreachable`（阻塞 L1–L5 全部 skip）。

## 根因

`ohos-prepare-isolated-conan-job.sh` 只创建 `conan-home/` 目录结构并写
`env.sh`，**不会**在新 CONAN_HOME 里添加私有 remote。runner 直接执行
`build_and_test.sh`，而 `ci/conan/setup.sh` 才是添加 `ohpcd`、禁用
`conancenter`、导入 ohos-aarch64 profile 的步骤——跳过它时 conan 对
ohpcd 一无所知。

## 解法（可复用流程）

手动隔离 job 在第一次跑 build_and_test.sh **之前**，先在 job 的 CONAN_HOME 里执行一次 setup.sh（注意设备 /tmp 只读，套 mktemp 包装）：

```sh
J=<job_base>                       # ~/ohos-users/codex/<job>
mkdir -p "$J/tmp"
export CONAN_HOME="$J/conan-home"
export TMPDIR="$J/tmp"; export TMPPREFIX="$TMPDIR/zsh"
cd "$J/repo/build_in_harmonyos"
zsh -c 'mktemp() { command mktemp -p "$TMPDIR" "$@"; }; . ./ci/conan/setup.sh'
conan remote list                   # 验证出现: ohpcd → https://conan.cnb.cool/...
```

之后再经 `ohos-test-runner.sh --lock` 重跑 build_and_test.sh。
一次性操作，job 存续期内有效；每个新 job 都要做。

## 鉴别要点

同样是 `registry_unreachable`：
- `Remote 'ohpcd' doesn't exist` → 本条（job 环境未初始化，先跑 setup.sh）；
- `system acceleration policy not enabled` → E477（CNB 对不存在包的响应，依赖真未发布，R36 问题）；
- 网络超时 → worker 网络，重试即可。

## 验证

reniced/1.23 r1 失败 → 按上述流程初始化后 r2 起 L0i 直接
`dependency in registry: perl/5.42.2.3`，r8 全门禁 pass exit 0。
