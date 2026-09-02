# DRAFT-libstatgrab-0.92.1-conandata-patch-lifecycle — 补丁未在 conandata 声明导致标准 Conan 生命周期不导出/不应用

> 对应 KV：`knowledge/drafts/DRAFT-libstatgrab-0.92.1-conandata-patch-lifecycle.kv`
> 触发事件：libstatgrab 0.92.1 HarmonyOS PC 适配 R02 审查修复（task_id `libstatgrab-0.92.1-r02-review-repair-path-b-pc2-12-20260902T051656Z`）

## 问题（error_signature）

`conan-init` 模板生成的 `conandata.yml` 初始为 `patches: {}`。当平台适配补丁文件已放入 `patches/` 目录、但未同步写入 `conandata.yml` 的 patches 列表时，Conan 2 的标准补丁生命周期完全失效：

- **不导出**：`export_conandata_patches()` 只导出被声明的 `patch_file`。声明缺失时 `conan export` 日志不出现 "Copied N '.patch' files"，导出缓存 recipe 目录内没有补丁文件。
- **不应用**：`apply_conandata_patches()` 在 build() 中只应用被声明的条目。声明缺失时 `conan create` 日志无 "Apply patch" 记录，build() 在未打补丁的源码上编译。
- **绕过陷阱**：为"绕过"此缺陷而在 build() 中手工 `replace_in_file` 做等价格式化替换，虽能编译，但补丁不进导出缓存、不被 apply 记录审计、CI 干净环境不可复现，且与补丁文件内容可能漂移不一致。

```text
# 症状 1：conandata.yml 有 patches/ 目录却 patches: {}
patches: {}

# 症状 2：conan export 日志无补丁拷贝
# （正确应为 "Copied 2 '.patch' files: ..."）

# 症状 3：conan create 日志无 Apply patch
# （正确应为 "Apply patch (portability): <描述>"）
```

## 根因（root_cause）

Conan 2 的补丁生命周期以 `conandata.yml` 的 `patches` 声明为**唯一事实来源**。声明缺失（或为空）时，`export_conandata_patches`/`apply_conandata_patches` 均静默跳过，没有任何报错——平台适配代码因此"无声失效"，或被人用 `replace_in_file` 在 build() 内手工等价替代掩盖。

## 解决方案（solution）

1. 在 `conandata.yml` 的 patches 列表声明每个补丁条目（`patch_file` 指向 `patches/` 下的文件，可附 `patch_description`/`patch_type`/`sha256`）。
2. `conanfile.py`：`export_sources()` 用 `export_conandata_patches(self)`，`build()` 用 `apply_conandata_patches(self)`；**不在 build() 中**用 `replace_in_file` 做等价格式化替代。
3. 重跑 `conan export` + `conan create`，以 export 日志 "Copied N '.patch' files" 与 create 日志 "Apply patch" 双重证明生命周期真实生效。

```yaml
# conandata.yml
patches:
  - patch_file: "patches/0001-<desc>.patch"
    patch_description: "<一句话>"
    patch_type: "portability"
    sha256: "<补丁 sha256>"
```

```python
# conanfile.py
def export_sources(self):
    export_conandata_patches(self)

def build(self):
    apply_conandata_patches(self)
    # 不再有 replace_in_file 等价格式化替代
```

## 验证（validation）

- 命令：`grep -A4 '^patches:' conandata.yml`；`conan export . --user=ohpcd --channel=stable 2>&1 | grep -E "patch"`；`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing 2>&1 | grep -E "Apply patch"`
- cwd：`/storage/Users/currentUser/.oh-runner/worktrees/libstatgrab-0.92.1/archives/l/libstatgrab/0.92.1`
- exit_code：0
- 日志：`/storage/Users/currentUser/tmp/statgrab-r02/conan-create-repair.log`
- sha256：`a0717b70574feae8c11accf3a7c71d4dec6c69ff4327996e7858dbb319f1be20`（tools.h 补丁）/ `ba8874237487ff8ecc19e9dee97a1f20d1139c6e4fc540695505dc3b21f850a0`（network_stats.c 补丁）
- 结果：conan export "Copied 2 '.patch' files"；conan create 两条 "Apply patch (portability)" 均真实应用，test_package 1/1 Passed

## 适用边界（scope）

- Conan 2.x recipe（`export_sources` 用 `export_conandata_patches`、`build` 用 `apply_conandata_patches`）且 `patches/` 目录含 `.patch` 但 `conandata.yml` patches 缺失/为空的所有包。
- 含补丁的平台适配（特性检测、config.sub/guess 修复、umask 修复等）尤为典型。
- 不适用：无补丁的纯配方、非 Conan 2 生命周期、依赖缺失类问题。

## 反例（counter-example）

- `conandata.yml` patches 列表格式错误、`patch_file` 指向不存在文件、补丁 strip 层级错误（见 E515/E526）、多源码包 base_path 配置（E282）——这些是补丁应用的**其他维度**，不是本条目覆盖的"未声明导致不导出/不应用"。
- 依赖未发布、registry 不可达（R36/R41）与本条目无关。

## 恢复条件（recovery）

在 `conandata.yml` 声明补丁（列表格式，补 patch_file + sha256）并删除 build() 中 replace_in_file 等价替代后，重跑 `conan export` + `conan create` 验证 "Copied N '.patch' files" 与 "Apply patch" 日志。

## 查重差异（dedup）

- 正式条目：E056（编辑器/补丁工具缩进）、E241（数据/规则清单库）、E248（patch mtime 致 automake 重生成）、E254/E484（toybox patch --dry-run）、E255（无编译库测试）、E256（二进制提交致 PR diff 失败）、E282（多源码 base_path）、E311（source-folder 隔离）、E321（Conan 1→2 迁移）、E416（大小写 slug）、E515/E526（patch strip 语义）、E528（autotools 环境闭合）、E542（provider 复用父制品）——**均非等价**；分析端已核 E102/E115/E140/E147/E148/E151 亦非等价。
- 草稿：`knowledge/drafts/` 无同 stem/等价草稿。
- 结论：四范围（formal/drafts/both/none）均无等价命中 → `match_result: none` → 新增价值成立。

## 基线排除（baseline_excluded）

- `archives/l/libXext/`（既有未触碰）；`SKILL.md`/`references/`/`templates/`/`scripts/`/`ci/`/`index.tsv`/`SUMMARY.md` 等框架文件；`feedback/`；正式 E### 条目；本库归档外的任何文件。

---
*created: 2026-09-02 · executor pc2-12 · based on libstatgrab 0.92.1 R02*
