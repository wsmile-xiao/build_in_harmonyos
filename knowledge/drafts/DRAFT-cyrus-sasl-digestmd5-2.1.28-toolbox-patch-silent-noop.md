# DRAFT-cyrus-sasl-digestmd5-2.1.28-toolbox-patch-silent-noop

> 本机 CLI `patch` 是 toybox 极简实现：对 `diff --git`/hunk 补丁**静默 no-op**（rc=0 且打印 `patching <file>`，源码实际未改）。补丁有效性证据必须来自 `patch_ng`/真实构建，不能取本机 `patch` 的退出码。

## 问题特征（真实日志片段）

```
$ patch --version
toybox 0.8.12

$ patch -p1 --dry-run < patches/0002-config-guess-config-sub-ohos.patch
patching config/config.guess
rc=0

$ patch -p1 < patches/0002-config-guess-config-sub-ohos.patch
patching config/config.guess
rc=0

$ diff -u .orig/config/config.guess .work/config/config.guess
（空 —— 文件实际未改，仅 mtime 更新）

$ ./configure ...
configure: error: cannot guess build type; you must specify one
```

对照：同一个补丁在 `conan create` 中由 Conan 自身 `patch_ng`（纯 Python，`apply_conandata_patches`）应用后**生效**：

```
cyrus-sasl-digestmd5/2.1.28: Apply patch (portability): config.guess: teach it HarmonyOS …
checking build system type... aarch64-unknown-linux-ohos
```

命中关键词：`toybox patch`、`diff --git`、`hunk header`、`silent no-op`、`patch rc=0`、`patching <file>`、`cannot guess build type`、`patch_ng`、`补丁未生效`、`假成功`。

## 根因

1. **工具语义缺失（平台/工具链）**：设备精简环境的 `patch` 是 toybox 0.8.12，只解析 `---/+++` 文件名，不实现 `diff --git` 头与 `@@ -a,b +c,d @@` hunk 区间；遇到不支持的内容既不报错也不落盘，仍返回 0。
2. **证据口径错误（流程）**：把"命令退出码 0"等价于"文件已改"是错误假设；本机 `patch` 下该假设必错。
3. **类别性**：属"精简工具语义缺失 + 证据判定口径"的通用问题，非 cyrus-sasl 单点；同类风险还有 busybox `patch`、精简 `sed/grep` 的扩展语义缺失。

## 使用说明

1. **何时用**：任何在 OHOS 设备/精简系统上"用 CLI `patch` 应用或验证源码补丁"的环节；尤其当补丁含 `diff --git` 头或你无法确认 `patch` 实现时。
2. **怎么用**：先看 `patch --version`（含 `toybox`/`busybox` 即不可信）→ 改用 `patch_ng` 或字节级编辑应用 → 用 `diff -u <pristine> <patched>` 或真实构建读数确认生效。
3. **判定口径**：补丁有效性三选一证据 = 与 pristine 的 diff 内容 / `patch_ng` `apply()` 返回 True / 构建日志中的实际效果（本例 `checking build system type... aarch64-unknown-linux-ohos`）。
4. **禁止**：仅凭 `patch` 退出码 0 宣称"补丁已应用"。

## 适用范围

- 在 OHOS 设备/精简系统上用 CLI `patch` 验证或应用源码补丁的所有流程；
- autotools 项目的 `config.guess`/`config.sub` 平台三元组补丁；
- 上游测试源码可移植性补丁、`conandata.yml` patches 的本地预验证；
- 任何把工具退出码当作"操作已生效"证据的判定环节。

## 输入 / 输出定义

- 输入：待验证的补丁文件 + 原始（pristine）源码树副本。
- 输出：布尔"是否真正应用"+ 证据（diff 内容 / `patch_ng` apply 结果 / 真实构建读数）。

## 修复方案（rec，优先级 1）

1. **本地勘探**：改源码用字节级编辑，保持行尾空白不变：

   ```python
   data = open(path, 'rb').read()
   assert data.count(old) == 1
   open(path, 'wb').write(data.replace(old, new))
   ```

2. **补丁有效性三选一证据**（禁止只看 `patch` 的 rc）：

   ```python
   from patch_ng import fromfile
   ps = fromfile("patches/0002-config-config.guess.patch")
   print("apply =", ps.apply(strip=1, root="/tmp/pristine-copy"))   # 期望 True
   ```

   ```bash
   diff -u <pristine>/config/config.guess <work>/config/config.guess   # 必须非空且与补丁一致
   ```

3. **端到端以真实构建为准**：`conan create` 日志出现 `Apply patch (…)`，且 configure 输出预期读数（如 `checking build system type... aarch64-unknown-linux-ohos`）。

4. **交付物**：补丁仍由 `refresh-patch --auto` 生成（不手写），并用 `patch_ng` 逐条 `apply=True` 复核。

## 回退方案（优先级 2）

无法引入 `patch_ng` 时：python 字节级替换 + `diff -u` 与 pristine 比对，确认改动范围最小（本例实测 `+1/-1`、`+11/-0`、`+2/-2` 三个补丁）。

## 禁止策略

- ❌ 仅凭 `patch -p1 … rc=0` 判定"补丁已应用" —— 本机实现可能静默 no-op；
- ❌ `sed -i` 直接原地改源码且不留补丁 —— 重新解包后丢失，CI 干净环境必然失败。

## 本任务实测

cyrus-sasl-digestmd5 2.1.28（autotools，OHOS aarch64 / clang 15.0.4）：
- `patch` = toybox 0.8.12 → 补丁 CLI 应用为静默 no-op（已用 `diff` 证实）；
- Conan `patch_ng` 应用 3/3 补丁成功（`apply=True`），`conan create` 中 `checking build system type... aarch64-unknown-linux-ohos`；
- 最终补丁规模：`0001-utils-testsuite.c.patch` +1/-1、`0002-config-config.guess.patch` +11/-0、`0003-config-config.sub.patch` +2/-2。
