# DRAFT — refresh-patch 重命名补丁并重置分类，使 conandata.yml 失配

> Status: DRAFT (contributor 8543) | Source: looktxt/1.4.1 adaptation, task #8543
> Environment: HarmonyOS PC aarch64, Conan 2.29.1 (OHOS), ohc finish（Step 1 refresh-patch → Step 4 conan-verify → Step 5 W3）

## 1. 症状

补丁内容与来源都正确，`conan create` 在补丁命名一致时也全程通过；但一旦重跑
`finish`，Step 4 就抛错，W3 完全没执行（`reports/w3-local-ci.log` 里只有导出期异常）：

```
ConanException: Patch file does not exist:
  '.../archives/l/looktxt/1.4.1/patches/0001-fix-eof-infinite-loop-int-c.patch'
  raised from export_sources()
```

目录里此时是：

```
patches/0001-looktxt.c.patch            ← 内容与自己手写版 diff 为空
patches/.patch-backup-20260919174335/    ← 自己命名的旧补丁被移进来
```

同时 `manifest.yaml` 尾部两块被工具重写：

```yaml
patch_generation:  source_work_hash: <新哈希>  generated_at: '<本次时间>'
patch_classification:
  - file: 0001-looktxt.c.patch
    type: auto            # 占位
    platform_only: True   # 占位
    guard: 'pending'      # 占位
```

## 2. 根因（读 `scripts/ohc/refresh_patch.py` 的 `auto_mode`）

- 输入不是 `conandata.yml`，而是 work 目录：优先用 `.edit-tracker.json` 的
  `edited` 列表（`scan()` 只做“与基线哈希不同就 append”，且 `edited` **永久累积、
  基线不刷新**），没有追踪器时退化为排除规则 diff；
- 输出文件名固定为 `f"{i:04d}-{rel_path.replace('/', '-')}.patch"`，
  即“序号-变更文件路径”，**与描述性命名无关**；
- 旧补丁整体搬进 `patches/.patch-backup-<ts>/`，新补丁替换到位；
- 最后无条件用 `re.sub` 删掉 manifest 尾部的 `patch_generation:` /
  `patch_classification:` 块并写回默认分类（代码注释自己写着 “AI should classify later”）。

于是任何“手工命名补丁 → 跑 finish”的顺序都会得到：补丁改名 + 元数据被重置。
`export_conandata_patches()` 按 `conandata.yml` 的旧名找文件，必然失败。

## 3. 处置（本案采用，并保证 finish 幂等）

1. **接受工具生成的规范名**：`conandata.yml` 的 `patch_file`、`manifest.yaml` 的
   `patches_applied`、`notes.md`，以及本地的 `reports/test-report.md`、`reports/pr-body.md`（两者按 PR 禁止文件清单不入库）全部
   统一为 `0001-looktxt.c.patch`，并在 `conandata.yml` 顶部与 `notes.md` 说明该名字由
   refresh-patch 生成、内容与人工命名版逐字节相同；
2. 删除 `.patch-backup-*`（自己的中间产物），重跑 finish →
   `G2 PASS` → `W3 通过` → `.ci-result.json`（门禁状态文件，按规则不入库）`exit_code=0`；
3. **最后一次 finish 之后**再人工回填分类为事实值：
   `type: portability / platform_only: false / guard: 'none'`（type 取 portability 以对齐
   code_style §12 的固定口径，与 `conandata.yml` 的 `patch_type` 同值），此后不再重跑 finish
   （`archives/i/is_utf8/1.4.1/notes.md` 问题表 P3 是同一坑的先例记录）。

## 4. 判别与自检

```sh
ls archives/<l>/<pkg>/<ver>/patches/                       # 只看工具名
grep -n "patch_file" archives/<l>/<pkg>/<ver>/conandata.yml # 必须逐字一致
tail -15 archives/<l>/<pkg>/<ver>/manifest.yaml             # guard 是否还是 pending
```

`guard: 'pending'` / `type: auto` 一旦出现即为占位值，不能作为提交态。

## 5. 与既有知识的关系

| 条目 | 覆盖 | 未覆盖 |
|---|---|---|
| E515 | refresh-patch 产出 `a/`+`b/` 前缀补丁，conan 需显式 `strip: 1` | 文件名接管与分类重置 |
| E282 | 多源码配方的逐条 `base_path` | 命名与元数据一致性 |
| E484 / E254 | toybox/OHOS `patch --dry-run` 污染 `.orig` 基线 | 追踪器 `edited` 永久累积导致每次必重生成 |
| E066 | 补丁管线只认 `.tar.gz` | 同一段管线的命名契约 |

本案的独立价值：给出“补丁存在却报不存在”这一类失败的最小判别路径，以及
“元数据回填必须排在最后一次 finish 之后”的操作顺序。
