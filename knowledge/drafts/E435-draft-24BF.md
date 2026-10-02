# E435 — 制品仓对不存在的配方返回 acceleration policy 报错（易误判为 registry 不可达）

> 草稿条目，来源：`rtl-wmbus/1.1.0` 适配 HarmonyOS PC（OHOS aarch64）。
> 状态：draft，待主编审核后 promote 为正式知识条目。

## 错误特征

```text
ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]
```

实际遇到的报错：

```text
conan download rtl-sdr/0.9.0 -r=ohpcd --only-recipe -> ERROR: error:system acceleration policy not enabled.
```

## 触发条件

- 分类：`registry`
- 阶段：`configuration`
- 工具：`conan`
- 适用范围：W0 依赖发布检查中，对制品仓探测一个尚未发布/不存在的配方版本时

## 根因分析

cnb.cool 制品仓的 Conan v1 兼容接口对“配方不存在”的查询返回 error:system acceleration policy not enabled，而不是 Recipe not found / 404。该文案与网络或鉴权无关，极易被误读为 registry 不可达，从而误触发 R41 重试与止损流程。（该文案由网关返回，其在“配方不存在”场景下的确切成因未在本条断言范围内；此处只固化可复现的现象与判定口径。）

## 解决方案

### 推荐方案

W0 依赖探测以 conan download <pkg>/<版本> -r=ohpcd --only-recipe 成功与否为权威判据（R35 口径）；conan search 仅可作为人工排查的辅助线索，不作为 binary 是否存在的依据（R35 明确 search API 对 binary 返回不完整）。看到 acceleration policy 报错应先按“该版本未发布”处理，而不是当作 registry 故障。

**方案说明**：用 conan download --only-recipe 判定依赖是否发布；acceleration policy 报错按“未发布”解读。

```bash
conan download rtl-sdr/2.0.2 -r=ohpcd --only-recipe   # 权威判据
grep -n "Recipe not found" conan_create.log            # 如需排查非法 recipe
```

### 禁止做法

- ❌ 不要把该报错当作网络/registry 故障而进入 R41 重试与止损流程；也不要用 conan list/search 判断 binary 是否存在（R35）。
  - 原因：该报错在“配方不存在”时出现，与连通性无关；search API 对 binary 的返回不完整。
  - 后果：误判 registry 不可达 → 无谓重试、超时，甚至错误地按 dependency_missing/env_unsupported 止损，浪费整轮适配。

### 回退方案

若需枚举制品仓已有版本，可人工用 conan search 查看，但结论仍需用 conan download 复核。

## 验证

```bash
conan download rtl-sdr/2.0.2 -r=ohpcd --only-recipe 成功；rtl-sdr/0.9.0 返回上述 acceleration policy 报错——由 rtl-wmbus/1.1.0 的 W0 探测实测。
```

## 关联条目

- 相关软件包：`rtl-wmbus/1.1.0`
- 完整踩坑记录：`archives/r/rtl-wmbus/1.1.0/notes.md` 第 7 节
