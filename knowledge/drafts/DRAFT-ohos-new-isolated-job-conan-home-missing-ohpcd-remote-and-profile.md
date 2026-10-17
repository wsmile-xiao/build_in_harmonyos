# DRAFT-ohos-new-isolated-job-conan-home-missing-ohpcd-remote-and-profile：真机新隔离 job 的 conan-home 缺 ohpcd remote / profile（L0i 必挂）

> Status: **Draft**（待审核 promote）| severity: `P1` | category: `platform` | Updated: 2026-09-27
> 对应: `knowledge/drafts/DRAFT-ohos-new-isolated-job-conan-home-missing-ohpcd-remote-and-profile.kv`

---

**匹配关键词**：Remote 'ohpcd' doesn't exist, registry_unreachable, conan-home, profile import, ohos-prepare-isolated-conan-job, L0i, R36

## 错误签名（error_signature）

```text
ERROR: Remote 'ohpcd' doesn't exist
# 且 L0i 报：
[error] registry unreachable for: <dep>/<ver>（conan stderr: Remote 'ohpcd' doesn't exist）
```

## 错误摘录（error_excerpt）

```text
[step] L0i: Checking dependency availability in registry (R36)...
        [error] registry unreachable for: xz/5.8.3.2
        conan stderr: ERROR: Remote 'ohpcd' doesn't exist
```

## 根因（root_cause）

ohos-prepare-isolated-conan-job.sh 给每个新 job 生成的 **conan-home 是全新缓存**：
remotes.json 只有 conancenter，没有制品仓 remote `ohpcd`；profiles 缓存为空。
build_and_test.sh 直跑路径（run-conan-heavy.sh → zsh ci/conan/build_and_test.sh）
**不经过** ci/conan/setup.sh，于是 L0i 探测依赖时 remote 不存在——CI 把它归类为
"registry unreachable（基础设施错误）"，看起来像网络故障，实际是环境未初始化。
第二个暗坑：setup.sh 里的 `conan profile import` 在该 conan 版本上**静默不生效**
（执行后 conan profile list 仍为空），profile 必须另行落位。

## 推荐方案（rec_approach）

新 job 首跑前，一次性初始化（幂等，全部 job 本地操作）：

```sh
. "$JOB/env.sh" && cd "$CI_REPO_ROOT"
zsh ci/conan/setup.sh                                 # 注册 ohpcd remote（匿名读）+ 禁 conancenter
mkdir -p "$CONAN_HOME/profiles"
cp "ci/conan/profiles/ohos-aarch64" "$CONAN_HOME/profiles/ohos-aarch64"  # profile import 静默无效，手动落位
conan profile list && conan remote list               # 双验证
# 预演 L0i（逐依赖）：conan download <dep>/<ver> -r=ohpcd --only-recipe
```

识别信号：真机 run 的 L0i 报 registry unreachable 且 stderr 是 "Remote … doesn't
exist"（而非网络超时）→ 不是网络问题，是 conan-home 未初始化。

## 复用价值

每个新隔离 job 首跑必经；可先在本机脚本里预演 L0i 三个依赖探测，再启动构建，
避免占用真机排队窗口。图谱查重 0 命中（2026-09-27，"Remote 'ohpcd' doesn't
exist" / "profile import" 均无条目）。
