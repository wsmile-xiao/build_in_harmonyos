# E543 — refresh-patch 新文件补丁被破坏（BusyBox patch --dry-run 在 orig 目录造 0 字节占位）

## 错误特征

conan create 在 build() 第一步 `apply_conandata_patches(self)` 失败，日志：

```
.../patches/0003-intltool-merge-shim.patch: source/target file does not exist:
  --- b'a/intltool-merge-shim'
  +++ b'b/intltool-merge-shim'
ERROR: ... ConanException: Failed to apply patch: .../0003-intltool-merge-shim.patch
```

补丁文件首行已不是 `--- /dev/null`，而是 `--- a/<path>`（新文件补丁丢失 /dev/null 标记）。

## 触发条件

- 工具链: refresh-patch --auto / `finish` step [1/10]（OHOS 环境 BusyBox patch）
- 阶段: conan create 的 build() 第一步（apply_conandata_patches）
- 前提: 配方 patches/ 中含「新增文件」类补丁（`--- /dev/null\n+++ b/<path>`），且已跑过一次 refresh-patch

## 根因分析

`refresh_patch.py` 的 `_dry_run()` 对每个生成的补丁在 orig 目录执行
`patch --dry-run -p1` 做校验。对 `--- /dev/null` 新文件补丁，BusyBox `patch --dry-run`
会在 orig 目录**实际创建**同名 0 字节占位文件（GNU patch 不会，BusyBox 会）。

下一次 refresh-patch 走编辑追踪器精准模式时，判断 `orig_file.exists()` 为 True，
于是把「新增文件」当作「修改文件」处理，用 `difflib` 对 0 字节 orig 文件生成 diff →
补丁首行变成 `--- a/<path>`（丢失 `/dev/null` 标记）。conan 的
`apply_conandata_patches` 把 `--- a/<path>` 当修改文件的源路径解析，源文件在目标树
不存在 → `source/target file does not exist`，conan create 在 build() 第一步即失败。

kylin-burner 3.0.11 实测：5 个新增文件（intltool-merge-shim、m4/ohos-stubs.m4、
m4/pkg.m4、ohos-stubs/canberra-gtk.h、ohos-stubs/gdk/gdkx.h）的补丁全部被破坏，
且每次 refresh-patch 运行都会在 orig 目录重新生成这些 0 字节占位文件。

## 解决方案

### 推荐方案

1. 删除 orig 目录下「新文件」对应的 0 字节占位文件（对照 conandata.yml/patches 中
   新增文件清单，`find <orig> -type f -size 0c` 复核），使 refresh-patch 重新走
   「新增」分支：
   ```bash
   O="<BUILD_SRC_ORIG_DIR>"
   rm -f "$O/intltool-merge-shim" "$O/m4/ohos-stubs.m4" "$O/m4/pkg.m4" \
         "$O/ohos-stubs/canberra-gtk.h" "$O/ohos-stubs/gdk/gdkx.h"
   ```
2. 重新跑 `refresh-patch --auto <软件> <版本>`（或直接 `finish`），确认日志中这些
   文件以「➕ 新增」出现，生成的补丁首行为 `--- /dev/null`。
3. `conan-verify` 复验：G2 conan create 通过、test_package 真实执行即恢复。

### 禁止做法

- ❌ 禁止手写/手工 sed 改补丁首行绕过（应先修根因：删除 orig 占位文件）
- ❌ 禁止删除出问题的补丁（应先按上述步骤重新生成）

## 验证

```bash
head -1 patches/0003-intltool-merge-shim.patch   # 应为: --- /dev/null
ls -la $BUILD_SRC_ORIG_DIR/intltool-merge-shim  # 应为不存在（0 字节占位已删）
python3 scripts/ohc-run.py conan-verify kylin-burner 3.0.11   # G2 PASS
```

## 关联条目

- 相关: E540（OHOS conan 运行时/工具链路径类），E058（补丁格式校验）
