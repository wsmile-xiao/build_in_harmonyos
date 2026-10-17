# DRAFT-orcania-2.3.2-refresh-patch-rename-conandata-mismatch — finish refresh-patch 重命名补丁导致 conandata.yml patch_file 引用失效

> 对应 KV：`knowledge/drafts/DRAFT-orcania-2.3.2-refresh-patch-rename-conandata-mismatch.kv`
> 触发事件：orcania 2.3.2 HarmonyOS PC 适配 r01 交付（task_id `orcania-2.3.2-r01-pc2-25-20260916T133924Z`）

## 问题（error_signature）

带 `patches/` 的库在 `finish` 流程（Step 1/10 refresh-patch --auto）后，`conan create`
在 `export_sources()` 阶段失败：

```text
ERROR: orcania/2.3.2: Error in export_sources() method, line 56
	export_conandata_patches(self)
	ConanException: Patch file does not exist:
	'.../archives/o/orcania/2.3.2/patches/0001-ohos-subunit-optional.patch'
```

## 根因（root_cause）

finish 的 `refresh-patch --auto` 基于编辑追踪器（.edit-tracker.json）扫描 work 目录变更，
按**生成时规则**重命名补丁文件为 `{NNNN}-{相对路径转连字符}.patch`（如
`0001-CMakeLists.txt.patch`），并把旧命名的补丁移入 `patches/.patch-backup-<ts>/`。
若 `conandata.yml` 的 `patch_file` 仍引用**手动命名**的旧名（如
`0001-ohos-subunit-optional.patch`），`export_conandata_patches()` 按声明路径找不到文件，
`conan create` 在 export 阶段直接失败——G2 / W3 全部阻塞。

区别于 E254/E484（toybox patch --dry-run 污染 .orig，导致**生成错误内容**的补丁）与
E515（补丁内容正确但缺 strip:1 参数）：本条是**补丁文件被重命名**导致
`conandata.yml` 的 `patch_file` **引用名失效**。

## 解决方案（solution）

以 refresh-patch 实际生成的文件名为准，同步 `conandata.yml` 的 `patch_file`：

1. `finish` 后检查 `patches/` 目录实际存在的 `*.patch` 文件名。
2. 将 `conandata.yml` 中对应条目的 `patch_file` 改为该真实文件名（如
   `patches/0001-CMakeLists.txt.patch`）。
3. 删除 `patches/.patch-backup-*/` 备份目录（避免 JC junk 拦截）。
4. 复跑 conan-verify（G2）与 finish W3 确认通过。

## 验证（verification）

- orcania 2.3.2：conandata.yml `patch_file` 与 refresh-patch 生成名对齐后，
  conan-verify G2 PASS（conan create 干净构建含上游 CTest）、finish W3 PASS
  （.ci-result.json exit_code=0）。
- 命令/日志：`conan create ... --build=missing`（G2，exit 0）、
  `ctest --test-dir build --output-on-failure`（4/4，exit 0）。

## 适用边界（boundary）

- 适用于所有带 `patches/` 目录且 `conandata.yml` 声明 `patch_file`、会被 finish
  refresh-patch --auto 重新生成的库。
- 手动保留自定义补丁名（不运行 refresh-patch 的库）不受影响。
- 若 conandata.yml 未声明补丁（patches 为空/缺失），属另一类问题
  （DRAFT-libstatgrab-0.92.1-conandata-patch-lifecycle），不在本条范围。

## 反例（counter-example）

- 补丁文件存在但内容错误、strip 参数缺失 → E254/E484/E515 覆盖，非本条。
- conandata.yml 未声明任何补丁而 patches/ 有文件 → libstatgrab 草稿覆盖。

## 关系（relations）

- `similar_to`: E515（refresh-patch/conandata patches 工具链同源）、
  E254/E484（同为 refresh-patch 产物与 conan 应用侧不匹配）
- `caused_by`: refresh-patch --auto 的补丁重命名规则 + conandata.yml 静态引用旧名
- `conflicts_with`: 无
- `prerequisite_of`: 无
