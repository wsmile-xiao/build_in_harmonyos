# E547 — OHOS patch --dry-run 对新文件补丁有副作用：污染 orig 目录导致补丁头退化为 a/ 路径

## 错误特征
- `conan create`（G2 干净源码构建）在应用补丁时报：`Failed to apply patch ... source/target file does not exist`
- 查看补丁文件发现新增文件的补丁头是 `--- a/<path>` / `+++ b/<path>`，而非正确的 `--- /dev/null` / `+++ b/<path>`
- orig 目录（refresh-patch 的原始源码副本）中出现 0 字节的新文件
- 典型触发链：第一次 `refresh-patch --auto` 成功 → 后续再次执行 refresh-patch 或 finish 内置补丁生成 → 补丁头退化

## 触发条件
- 构建系统: 任意（本条目与构建系统无关，属于补丁管线工具链问题）
- 阶段: patch 生成/应用（conan create 的补丁应用阶段暴露）
- 环境: OHOS PC（本机 patch 命令对 `--- /dev/null` 头补丁执行 `patch --dry-run -p1` 验证时，会在 cwd（orig 目录）创建 0 字节目标文件——dry-run 产生了实际副作用）

## 根因分析
1. `refresh-patch --auto` 生成补丁前会用 `patch --dry-run` 验证现有补丁；
2. 对"新增文件"型补丁（头为 `--- /dev/null`），OHOS 的 patch 在 dry-run 时错误地在 orig 目录创建了 0 字节的目标文件；
3. 下一次 refresh-patch（或 finish 内置步骤）的 `diff_pairs` 收集阶段检查 `orig_file.exists()`——污染文件使新文件被误判为"已存在"，走 `_diff_files`（双文件 diff）而非"新文件"路径；
4. `_diff_files` 生成 `--- a/<path>` 头，GNU patch 在干净源码树上应用时报 `source/target file does not exist`，conan create G2 失败。

## 解决方案

### 推荐方案
1. 诊断：`find work/orig -size 0` 找出 0 字节污染文件；对比 `patches/.patch-backup-*/` 两代补丁头确认退化；可用 `work/.edit-tracker.json` 的 baseline 哈希校验 orig 纯净度
2. 修复：删除 orig 中的 0 字节污染文件 → `refresh-patch --auto` 重新生成（补丁头恢复 `--- /dev/null`）→ **再次检查并清理 orig**（dry-run 副作用会重现）→ 立即 `finish`
3. 预防：连续两次 refresh-patch 之间必须检查并清理 orig 目录

```bash
find work/orig -size 0 -delete
python3 $SKILL_ROOT/scripts/ohc-run.py refresh-patch --auto <软件名> <版本>
find work/orig -size 0 -delete   # dry-run 副作用重现，再清一次
python3 $SKILL_ROOT/scripts/ohc-run.py finish <软件名> <版本> published
```

### 禁止做法
- ❌ 在 orig 被污染状态下反复执行 refresh-patch --auto（副作用稳定重现，补丁头稳定退化）
- ❌ 手动编辑补丁文件把 `--- a/<path>` 改回 `--- /dev/null`（绕过管线一致性，下次 refresh 会再错，且 CI 干净环境仍可能失败）
