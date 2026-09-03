# DRAFT-ohos-conan-copy-fnmatch-anchored：conan copy() fnmatch 锚定全路径匹配

> Contributor: nymphcast-0.2 适配 | Status: Draft（扩展项，合并候选） | 2026-08-27
> Source: archives/n/nymphcast/0.2-alpha0（package()）+ Auditor B3-1

## 现象

nymphcast 的 Makefile 把产物输出到 `bin/<triple>/nymphcast_server`
（`TARGET_BIN` 含工具链 triple 子目录）。conanfile.py `package()` 最初用
`copy(self, "nymphcast_server", src_dir, dst)` 匹配 0 个文件，产物缺包。

## 根因分析（conan 2.29.1 copy_pattern.py 源码核验）

`conan.tools.files.copy` 的 pattern 经 `fnmatch.fnmatch(os.path.normpath(相对路径))`
对**相对 src 的完整路径**做锚定匹配。设备 python3 实测：

```python
fnmatch.fnmatch("bin/aarch64/nymphcast_server", "nymphcast_server")   # False
fnmatch.fnmatch("bin/aarch64/nymphcast_server", "**/nymphcast_server") # True
```

即 fnmatch 的 `*` **不跨 `/`**；子目录产物必须用 `**/name` 或前导 `*name`。

## 解决方案

```python
copy(self, "**/nymphcast_server",
     os.path.join(server_dir, "bin"),
     os.path.join(self.package_folder, "bin"), keep_path=False)
```

`keep_path=False` 平铺进入 package `bin/`，使可执行文件在 conanrun PATH 上。
round-9 CI PASS，test_package `--version` 真实运行验证产物存在。

## 合并建议（B3-1 补证吸收）

Curation Auditor 复核指出：本机制的最相近既有条目除
**E320-draft-GLOB-LOCATE**（cargo 产物 glob 递归定位，主题= glob 递归定位）外，
还有 **DRAFT-conan-copy-keep-path-nesting**（conan copy pattern/keep_path 语义，
alexjs 触发）——Curator 查重列表遗漏了后者。两者与本条目的差异：

| 条目 | 机制 | 与本条差异 |
|------|------|-----------|
| E320-draft-GLOB-LOCATE | glob 递归**定位**产物绝对路径 | 本条目是 **copy() pattern fnmatch 锚定**，不跨 `/` |
| DRAFT-conan-copy-keep-path-nesting | **keep_path 嵌套**陷阱（目录名再套一层/静默空目录） | 本条目是 **fnmatch `*` 不跨 `/`**（匹配不到） |

建议：本条可并入 E320-draft-GLOB-LOCATE 的机制说明，或与
DRAFT-conan-copy-keep-path-nesting 合并为"conan copy pattern 语义"组合条目；
最终由知识库主编决定。

## 验证证据

- round-9 权威 CI PASS；conan create 后 package 内 bin/nymphcast_server 存在。
- fnmatch 行为设备 python3 实测（True/False 见上）。

## 禁止做法

- 不要对子目录产物用无 `*`/`**` 前缀的单段 pattern（fnmatch 锚定 0 匹配）。
