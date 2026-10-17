# DRAFT-conan-cache-db-zombie-rows：conan cache DB 僵尸行——list 可见、create 报 not found

> Contributor: j669539 | Status: pending-editor-review | Updated: 2026-10-01
> Source: PR #14229 kshisen 26.04.0 适配，本机 conan 2.29.1-OHOS 修复实战

## 错误特征

```text
ERROR: Package 'kcrash/6.18.0' not resolved: kcrash/6.18.0: Cannot load recipe.
Error loading conanfile at '/storage/.../.conan2/p/kcras2a4b2932ef5ca/e/conanfile.py':
/storage/.../.conan2/p/kcras2a4b2932ef5ca/e/conanfile.py not found!. Required by 'kshisen/26.04.0'
```

- `conan list` / `conan info` 正常显示包存在（读 DB 索引）；
- `conan cache path <pkg>/<ver>` 报 `'export' folder does not exist for the reference`；
- `conan create/install` 解析依赖图时在早期（依赖安装阶段）报 `Cannot load recipe`；
- conan 误提示 `Recipe seems broken / not Conan 2.0 ready`——**误导方向**：看似配方问题，实为 cache 索引与磁盘失同步；
- OHOS 适配版 conan 上 `conan remove <ref>` 对僵尸行**挂死**（实测两次 300s+ 无输出，stdin=/dev/null 也不退出，必须 kill）。

## 根因

conan 2.x 的包缓存索引在 `~/.conan2/p/cache.sqlite3`：

- `recipes` 表：`reference / rrev / path / timestamp / lru`
- `packages` 表：`reference / rrev / pkgid / prev / path / build_id / lru`

`path` 字段即 `p/<hash>` 相对目录。当磁盘目录被外部清理（CI cleanup.sh 全量重置、磁盘清理、拷贝恢复只还原部分目录）而 DB 行残留时产生"僵尸行"：DB 说有、磁盘没有。一次实测扫描出 **2156 条僵尸配方行 + 306 条僵尸二进制行**（含 karchive/kcrash/kconfigwidgets/kcoreaddons/kdbusaddons/ki18n/kxmlgui/solid/openal-soft 等 19 个 KDEGames6 图直接依赖）。

## 处理流程（四步 sqlite 手术）

1. **备份**：`cp ~/.conan2/p/cache.sqlite3{,.bak-$(date +%Y%m%d-%H%M%S)}`；
2. **只读扫描**：python3 sqlite3 遍历两表，对每行取 `path`，判断 `~/.conan2/p/<path>/e`（配方）或 `~/.conan2/p/<path>/p`（二进制）目录是否存在；
3. **删除僵尸行**：
   ```sql
   DELETE FROM recipes WHERE reference=?;
   DELETE FROM packages WHERE reference=? AND pkgid=?;
   -- commit
   ```
4. **重跑**：`conan create . --build=missing`——conan 从 ohpcd 远端重取被删引用的配方与 prebuilt 二进制；其余大量 `Already installed` 依赖不受影响。

验证：`conan cache path <pkg>/<ver>` 返回真实路径，不再报 export folder 不存在。

## 验证

PR #14229 kshisen 26.04.0：

- 手术前：`conan create` 首跑即报 kcrash/6.18.0 `Cannot load recipe`（19 个直接依赖全为僵尸行）；
- 手术后：剩余 649 配方/938 二进制全部磁盘可解析；`conan create` exit=0（35 依赖图一次通过，movetest 1/1 通过、test_package 四断言 PASS）；
- CI #66420 全绿（L0/L1 门禁 + test_package 通过）。

## 关联条目

- DRAFT-ci-worker-gate-fork-oom（资源故障类）：签名相似（create 早期失败）但根因与处理完全不同——先认签名再动手；
- 绝不要按 `Recipe seems broken` 提示去改配方（同一配方远端完好）。

## 兜底

不便动 DB 时：换 `CONAN_HOME` 指向新目录全量重建（代价是全部依赖重新下载）。
