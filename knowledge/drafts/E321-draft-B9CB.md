# E321 — CNB 制品仓对不存在包返回 "system acceleration policy not enabled"

> **结构化数据**: [E321-draft-B9CB.kv](E321-draft-B9CB.kv) (draft) | **原则**: R36
> **严重度**: 🟡 medium | **分类**: conan, network, detection

---

## 错误特征

```
[retry] registry probe 1/3 failed for zita-alsa-pcmi/0.6.1 (transient?), retrying...
[error] registry unreachable for: zita-alsa-pcmi/0.6.1
conan stderr: Connecting to remote 'ohpcd' anonymously ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]
[fail] L0i: Registry unreachable (infra error, not R36 violation): zita-alsa-pcmi/0.6.1
```

## 触发条件

- 工具: `conan download <ref> -r=ohpcd --only-recipe`（CI L0i 门禁内部）
- 阶段: 安装/门禁检查（conan-build-test 步骤）

## 根因分析

CNB（cnb.cool）Conan 制品仓对**匿名下载不存在/未发布的 recipe** 返回的错误文本是
`ERROR: error:system acceleration policy not enabled`，而不是标准的
`not found` / `404`。实测验证：

```bash
# 不存在的包 → 返回该错误文本（exit=1）
conan download "nonexistent-xyz/9.9.9" -r=ohpcd --only-recipe
# ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]

# 已发布的包 → 成功（exit=0）
conan download "zita-alsa-pcmi/0.6.1" -r=ohpcd --only-recipe
```

`ci/conan/build_and_test.sh` 的 L0i 门禁只把
`unable to find|does not exist|not found|404` 识别为"真未发布 (R36)"，
CNB 特有文本落入"网络/认证异常 (registry_unreachable)"分支，
提示"修复 worker 网络"，**实际是依赖尚未发布到制品仓**。

## 解决方案

### 推荐方案
1. 用 `conan list <dep>/<ver> -r=ohpcd` 核实依赖是否真的已发布；
2. 若未发布 → 先合入并发布该依赖（R36），再在 PR 评论 `/rebuild` 触发 CI；
3. 若已发布但仍失败 → 瞬时网络抖动，重试即可（L0i 已内置 3 次重试）。

### 禁止做法
- ❌ 看到 `registry_unreachable` 就当作 worker 网络故障，不核实依赖发布状态
- ❌ 用本地 conan 缓存绕过 L0i 远端探测（欺骗性修复，干净 worker 上仍会挂）

## 验证

```bash
conan list "<dep>/<ver>" -r=ohpcd
conan download "<dep>/<ver>" -r=ohpcd --only-recipe
```

## 关联条目

- 相关: E017（网络超时类，需与"包不存在"区分）
