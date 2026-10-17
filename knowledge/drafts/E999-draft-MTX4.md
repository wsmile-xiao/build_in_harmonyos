# E999-draft-MTX4 — 判断依赖是否已发布必须读 `conan graph info` 的 `binary` 字段；`conan download` 的退出码会给出反向结论

> **状态**：`draft: true`（路径 B 候选）
> **来源**：mtxclient 0.10.1 适配（PR #13832，commit `c22afd92f4`）
> **平台**：与平台无关（W0 预检方法学）
> **关联**：R35（禁止用 list/search 判断 binary）、R36（依赖先发布再构建下游）
> **非重复声明**：四范围查重对该判据/失效模式零命中。

## 错误特征

按 W0 做依赖发布检查时，一个**已经发布**的依赖被判成「未发布」：

```
$ conan download coeurl/0.3.2 -r=ohpcd --only-recipe
... packages
    No packages found for this revision
$ echo $?
0                      ← 注意：这里退出了 0

$ conan download coeurl/0.3.2 -r=ohpcd --only-recipe     # 另一次
ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]
$ echo $?
1                      ← 同一 ref，同一命令，这次退出 1
```

`conan graph info` 对同一 ref 的结论却相反：

```
$ conan graph info --requires=coeurl/0.3.2 -pr:h=... -pr:b=... -f=json
    coeurl/0.3.2 ... binary: Cache        ← 制品就在制品仓
```

本库首轮适配因此把整任务误判为「W0 阻塞（依赖未发布）」并标记 `blocked`。

## 根因

以 `conan download` 的**退出码**作为「是否已发布」的判据会同时踩两类失真：

| 失真 | 表现 | 后果 |
|------|------|------|
| (a) 只匹配到 recipe、无匹配当前 profile 的 binary | 打印 `packages: No packages found for this revision`，**仍然 exit 0** | 无法用退出码区分「有 recipe 无 binary」与「正常下载」 |
| (b) 网关/网络抖动 | `ERROR: error:system acceleration policy not enabled`，exit≠0 | 把**已发布**的依赖判成未发布 |

两者叠加 = 反向结论。

补充：仓库内两个预检工具都基于制品仓 **search API**：

- `ci/scripts/preflight_check.sh`
- `scripts/ohc/preflight.py`（`probe_registry()`）

而 **R35 已明确指出该 search API 对 binary 返回不完整**（会出现"显示没有但实际已上传"）。
因此它们报 `ok=True` 也不能反推 binary 齐全，`ok=False` 更不能反推 binary 缺失。

## 触发条件

任何按 W0 / R36 做依赖发布检查的场景，尤其是多层依赖链——一次误判会把**可推进的任务整轮停掉**。

## 推荐方案

以 `conan graph info` / `conan install` 的节点 `binary` 字段为**唯一判据**：

```sh
# 单个依赖
conan graph info --requires=coeurl/0.3.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -f=json

# 整包（同时对全部依赖与传递依赖定性）
conan graph info archives/m/mtxclient/0.10.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -f=json
```

判读：

- `binary: Cache` / `Download` → 有制品
- `binary: Missing` → 确实没有
- 同时检查 `graph.error` 为 `null`

提取一行式：

```sh
conan graph info --requires=<ref> -pr:h=<h> -pr:b=<b> -f=json | python3 -c "
import sys, json
d = json.load(sys.stdin)
for v in d['graph']['nodes'].values():
    if v.get('ref'):
        print(v['ref'], '->', v.get('binary'))"
```

### 注意：build 上下文要在目标平台复核

若宿主 profile 与构建 profile 不同（例如在 Windows 上查 OHOS 的 `tool_requires`），
构建上下文的节点会显示 `Missing`，**这不代表未发布**：

```
pkgconf/3.0.6  context: build  binary: Missing   ← 在 Windows 上查是正常的
pkgconf/3.0.6  context: build  binary: Download  ← 在设备上（-pr:b 亦为 OHOS）才是真相
```

### 验证

本库实测：改用 `graph info` 后确认 11/11 依赖（含 `coeurl/0.3.2`、`pkgconf/3.0.6`）均可用，
W0 结论由「阻塞」更正为「通过」，随后真机 `conan create` 一次跑通（100%）。

## 回退方案

若环境无法运行 `graph info`，对同一 ref 做带间隔的多次 `download`，
并以**输出文本**（是否出现 `Downloading recipe`/`Package installed`）而非退出码判定；
同时保留完整输出供人工复核。这只是兜底——(a) 类失真会持续存在。

## ★ 禁止策略 ★

- 不要用 `conan list "*/*:*/*"` 或 `conan search` 判断 binary 是否存在（R35）。
- 不要写 `if conan download ...; then ... else "未发布"` 这类**仅凭退出码**的分支。

## 备注

这条的代价值得记录：因为一次反向判据，本库先被判成阻塞、写了整套「阻塞分析」，
复测后才更正。**教训是「判据本身要先被验证」**——尤其当判据来自包装脚本的返回值时。
