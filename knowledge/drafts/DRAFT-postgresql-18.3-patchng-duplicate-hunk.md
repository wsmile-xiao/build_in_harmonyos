# DRAFT-postgresql-18.3-patchng-duplicate-hunk

> 草稿知识项 — conan patch_ng 对补丁重复 hunk 段的兼容行为实测结论
> 来源：postgresql 18.3 Conan 配方化（feat/postgresql-18.3，2026-09-03）
> 同 stem 配对：`knowledge/drafts/DRAFT-postgresql-18.3-patchng-duplicate-hunk.kv`

## 问题（现象 / error_signature）

- 手动构建时代的历史补丁（GNU patch 应用）在迁移到 conan 配方时，担心
  conan 2.29.1 的 patch_ng（纯 Python 实现）对补丁中的重复 hunk 段
  （同一文件同一上下文出现两段，如 miscinit.c）行为与 GNU patch 不一致。
- 常见误判路径：以为必须先去重/清洗补丁才能进 `conandata.yml`，
  从而破坏与手动构建基线的零偏离（W0b 原则）。

## 根因（root_cause）

1. conan 2.29.1 默认用 patch_ng 替代外部 patch 命令，无 `--fuzz`/`--forward`
   等 GNU 选项语义。
2. patch_ng 对"重复内容/疑似已应用"的判定逻辑独立实现，
   不能用 GNU patch 行为外推。
3. 事实上（实测）patch_ng 对该形态补丁 `apply=True`，
   目标文件恰好应用一次，不产生双重应用。

## 可复用方案（rec_approach: verify-patchng-compat-keep-original）

1. **先试后定**：在临时源码副本上用 patch_ng 试应用补丁（不改仓库文件）。
2. **断言两点**：apply 返回 True；应用后关键守卫宏/标记的计数符合"恰好一次"
   （如 `grep -c __OHOS__ miscinit.c` = 4、`grep -c getgroups` = 1）。
3. **通过则原样保留**：补丁进 `patches/` + `conandata.yml`
   （patch_description 完整描述），零偏离沿用历史补丁。
4. **仅当真实拒绝时**才做 GNU patch 兼容性调整（拆分/去重），
   并在 notes.md 记录偏离理由。

## 适用条件

- 从手动构建（GNU patch）迁移到 conan 配方的软件；
- 历史补丁含重复 hunk 段或疑似 already-applied 内容；
- conan 2.29.x（patch_ng）环境。

## 反例（不适用场景）

- 新生成的补丁（应直接产出无重复 hunk 的干净补丁，不需要本条）；
- patch_ng 明确拒绝（报 already applied / hunk failed）的场景——此时按第 4 步处理，不要硬套"原样保留"。

## 验证证据（真实命令 + 结果）

- 临时副本上 patch_ng 试应用：`apply=True`；
- 应用后 `grep -c __OHOS__ src/backend/miscinit.c` = 4、
  `grep -c getgroups src/backend/miscinit.c` = 1（恰好一次）；
- `conan create` 走 `apply_conandata_patches` 全流程，conan-verify G2 PASS，
  W3 本地 CI 全绿。

## 后续修正（2026-09-04，评审轮实测）

- **patch_ng 宽容 ≠ 补丁可移植**：同一补丁在 `git apply --check -p1`
  （严格模式，干净树）下**必败**——git 对"同一文件同一上下文出现两段 hunk"
  报 semantic conflict，且原补丁 hunk 行计数有偏差（GNU patch 靠 fuzz 容忍）。
  AI Review / 任何用 git apply 复现补丁的消费者都会踩坑。
- **结论修正**："patch_ng 通过" 只说明 conan 构建链路可用；入库补丁应同时满足
  双引擎验证：`git apply --check -p1` + patch_ng（conan 实际调用形态，
  strip=0 相对路径）。
- **最终处置**：本轮借评审意见（宏重命名）改用 `git diff` 从已验证源码树
  重新生成补丁（精确 hunk 计数、无重复段、miscinit.c 只出现一次），
  双引擎干净通过。历史补丁能重生成时优先重生成，"原样保留"仅在不允许
  改写的场景（如第三方只读补丁）才依赖本条的双引擎验证结论。

## 限制与恢复条件

- 结论基于 conan 2.29.1 实测；conan 升级若更换补丁后端需重新验证；
- 若补丁还包含"新增文件"（new-file）hunk，需另行注意
  patch_ng 与 toybox patch 的 new-file 行为差异（参考 E258）；
- `git diff` 重生成补丁时必须以**已验证构建通过的源码树**为基准 diff，
  否则会把树内其他未验证改动一起带入（生成前 `git status` 复核改动面）。
