# E254 — toybox patch --dry-run 会真实应用 new-file 补丁，污染 orig 目录

## 错误现象

`refresh-patch --auto` 生成的补丁被 `conan create` 的 `apply_conandata_patches()`
拒绝：

```
Error in source() method, line 102
  apply_conandata_patches(self)
  ConanException: Failed to apply patch: .../patches/0002-xxx.patch
  --- b'a/compat/xxx'
  +++ b'b/compat/xxx'
  source/target file does not exist
```

下一轮 `refresh-patch` 把原本的 new-file（新增源码）误判为 MOD（修改文件），
生成带 `a/` `b/` 前缀的 diff，`patch_ng`（conan 补丁引擎）无法应用。

## 根因

HarmonyOS 默认 `/usr/bin/patch` 是 **toybox 0.8.12**。实测确认：

```sh
$ printf '--- /dev/null\n+++ b/new.txt\n@@ -0,0 +1,2 @@\n+hello\n+world\n' | patch --dry-run -p1
creating new.txt        # ← dry-run 却真实创建了文件！
```

toybox 的 `patch --dry-run` 对 **new-file 补丁**（`--- /dev/null` → `+++ b/...`）
会真实创建文件，忽略 dry-run 语义；但对 **修改文件 diff** 则正确地不落盘。

`refresh-patch` 的 `_dry_run()` 校验在 pristine `orig/` 目录执行，
new-file 补丁被真实应用 → `orig/` 被污染 → 下一轮 `filecmp` 把该文件归为
`diff_files`（MOD），生成 `--- a/... / +++ b/...` 格式 → `patch_ng` 无法解析。

## 推荐方案：新增源码走 export_sources，补丁只留修改文件

把新增的源码（compat/、tests/ 等）从补丁移出，改为 conanfile.py
`export_sources()` 传递；`conandata.yml` 只保留修改文件（Makefile.am、
configure.ac 等）的补丁。

```python
# conanfile.py
from conan.tools.files import copy

def export_sources(self):
    export_conandata_patches(self)
    copy(self, "*", src=os.path.join(self.recipe_folder, "compat"),
         dst=os.path.join(self.export_sources_folder, "compat"))
    copy(self, "*", src=os.path.join(self.recipe_folder, "tests"),
         dst=os.path.join(self.export_sources_folder, "tests"))
```

> conan 会在 `source()` 执行前把 export sources 自动 merge 进 source 目录
> （`config_source` → `merge_directories`），无需在 `source()` 里再 copy。

`conandata.yml` patches 段只列修改文件：

```yaml
patches:
  - patch_file: "patches/0001-Makefile.am.patch"
    patch_description: "..."
    patch_type: "platform"
```

## 验证

```sh
# 验证 toybox 是否中招（输出 "被真实创建" 即中招）
printf '--- /dev/null\n+++ b/t.txt\n@@ -0,0 +1,1 @@\n+x\n' | patch --dry-run -p1
ls t.txt 2>/dev/null && echo "被真实创建"

# 验证补丁可被 patch_ng 应用
python3 -c "
import patch_ng
ps = patch_ng.fromfile('patches/0001-Makefile.am.patch')
print(ps.apply(root='.', strip=1))
"
```

## 案例

- abiword-plugin-clarisworks 3.0.8（2026-08-05）：W3 finish 阻塞，改 export_sources
  后 conan create 全绿（make check PASS + test_package PASS）。
- 同类参考：aaphoto 曾用 GNU patch 方案（fallback）。

---
source: knowledge/graph/draft/E254-draft-75E1.kv
draft: true
