# DRAFT — 配方已合入但制品从未上传：必须重出修订号

- **来源**: libxmu 1.3.1.1（X.Org libXmu，autotools，OHOS aarch64），source_pr 13894，2026-09-30
- **同 stem 草稿**: `DRAFT-libxmu-1.3.1.1-merged-but-unpublished-needs-recut.kv`

## 问题

`libxmu/1.3.1` 的配方早已合入 main，但：

```bash
$ conan list 'libxmu/*' -r=ohpcd
Connecting to remote 'ohpcd' anonymously
Found 0 pkg/version recipes matching libxmu/* in ohpcd
```

下游 `libxaw/1.0.16` 解析 `libxmu/1.3.1` 时报：

```
acceleration policy not enabled
```

该报错**不是网络抖动**，而是「远端确定性没有这个包」的信号。用兄弟包自证即可区分：

```bash
$ conan list 'libxext/*' -r=ohpcd     # 6.4.0 / 6.4.0.1 —— 有
$ conan list 'libxmu/*'  -r=ohpcd     # 0 条 —— 没有
```

## 根因

Conan 制品的**构建**与**上传**是两个阶段，且分属不同流水线：

| 阶段 | 触发者 | 做什么 | 上传制品？ |
|------|--------|--------|-----------|
| PR 校验 | PR 的 push / `/rebuild` | `conan create` + 测试 | **否** |
| 正式发布 | **PR 合并到 main 之后** | setup → build_and_test → **upload** → sign | 是 |

`ci/conan/upload.sh` 里有硬门禁：

```bash
if [ "${CI_TASK_TYPE:-}" != "release" ]; then
  exit 1        # PR 流水线不得上传
fi
```

因此，如果某版本在**合并那一刻**构建失败（本例：合入时 `libxext/6.4.0` 的匹配二进制
尚未产出，conan 回退源码构建，libtool 链接 `libxcb.la` 失败），它既没有制品，
也**不会**被任何后续操作重试——能触发上传的那次合并事件已经过去了。

后果有两个，都很隐蔽：

1. **修配方源码救不回来**。把配方改对再 merge 一次，只是在 main 上加了个新提交；
   版本号没变，发布流水线不会重新跑 `conan create` + `upload`。
2. **下游被永久阻塞**。任何 `requires("libxmu/1.3.1")` 的配方，解析阶段就失败，
   且报的是那句与「包不存在」毫无字面关联的 `acceleration policy not enabled`。

## 方案（推荐，已实测）

保持上游源码、sha256、补丁集**完全不变**，只把版本号加一位修订位，重出配方目录：

```
archives/l/libxmu/1.3.1      ->  archives/l/libxmu/1.3.1.1
```

```
version = "1.3.1.1"          # conanfile.py
```

上游并没有 1.3.2，`.1` 是本仓的**配方修订号**，用于触发一次全新的发布流水线。

重出版本里必须**同时消除当初导致构建失败的条件**，否则新流水线会以同样方式失败。
本例三件事同时成立才通：

1. 阻塞依赖的新修订 `libxext/6.4.0.1` 已上架（其配方自带 `_fix_dep_la_files`）；
2. `self.requires("libx11/1.8.13", force=True)` —— 统一整张图的 libx11 版本，
   消除 6.4.Z 与 1.8.Z 的冲突；
3. `generate()` 为直接依赖合成 libtool `.la` shadow（见同批草稿
   `DRAFT-libxmu-1.3.1.1-conan-deps-lack-libtool-la-shadow-synth`）。

重出时务必同步更新 `conandata.yml` / `manifest.yaml` / `notes.md` / `test_package/`，
并在 `notes.md` 里写清「为什么重出」。否则评审会把它当成一个无意义的新版本号。

## 验证

```bash
$ conan inspect archives/l/libxmu/1.3.1.1        # name=libxmu version=1.3.1.1
$ conan graph info archives/l/libxmu/1.3.1.1 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd
# libxt/1.3.1, libx11/1.8.13, xorgproto/2025.1, libxau/1.0.11, libxcb/1.17.0,
# libxdmcp/1.1.5, libsm/1.2.6, libice/1.1.2 均解析成功；仅 libxext/6.4.0.1
# 为 Missing，在 force 后的 libx11/1.8.13 轨道上源码重建。
$ conan list 'libxmu/*' -r=ohpcd                 # 0 条 -> 本修订为首次上传
```

## 适用边界与反例

- **适用**：`conan list '<pkg>/*' -r=<remote>` 查不到制品，且该版本号已经合入过 main。
- **不适用/反例**：版本从未合并过（那就是普通的一次新适配，直接正常提交即可）；
  或平台提供了对已合并版本重跑发布任务的入口（此时可在原版本上重跑 upload，无需新版本号）。

## 与既有知识的关系

- `similar_to DRAFT-vips-8.18.4.1-meson-codec-feature-pkgconfig`：同样以「.1 修订位」
  的方式重出配方，但那条讲的是修 Meson 特性探测，本条讲的是**为什么必须重出**
  （上传时机与合并事件绑定）。
- 与 `DRAFT-...-conan-deps-lack-libtool-la-shadow-synth` 互补：那条解决「重出版本怎么才能构建成功」，
  本条解决「为什么要重出、以及不重出为什么永远不通」。

## 查重表（四范围）

| 范围 | 结果 |
|---|---|
| 正式知识 knowledge/graph | 未命中（无「制品上传时机 / 重出修订号」条目） |
| 图谱 index.tsv | 未命中 |
| 草稿 knowledge/drafts/ | 未命中（`重出` / `修订号` 关键词无命中；只有 vips 一条相似但主题不同） |
| recipes catalog | libxmu 无既有制品记录 |
