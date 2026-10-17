# DRAFT-matchit-r01-conan-copy-pattern-dir-keep

> Contributor: junshi_liu | Status: Draft | Updated: 2026-09-02
> Source: matchit 1.0.0 HarmonyOS PC Path B adaptation (task matchit-1.0.0-r01-pc1-19-20260902T132357Z)
> 对应 KV: knowledge/drafts/DRAFT-matchit-r01-conan-copy-pattern-dir-keep.kv

## 主题 / 触发场景

Conan 2 配方 `package()` 中使用 `conan.tools.files.copy` 安装头文件时，
pattern 含目录层级且 `dst` 也含同目录名，落盘成 `include/include/` 双层嵌套，
CMakeDeps 的 `INTERFACE_INCLUDE_DIRECTORIES` 指向单层 `include`，consumer
`#include <xxx.h>` 在 `conan create` 的 test_package 编译阶段报 `file not found`。

## 现象 / error_signature

```text
test_matchit.cpp:4:10: fatal error: 'matchit.h' file not found
#include <matchit.h>
         ^~~~~~~~~~~
1 error generated.
```

包目录实测：

```text
package_folder/include/include/matchit.h   # ← 双层，错误
package_folder/licenses/LICENSE
```

CMakeDeps 生成 data cmake：

```cmake
set(matchit_INCLUDE_DIRS_RELEASE "${matchit_PACKAGE_FOLDER_RELEASE}/include")
```

## 根因 / root_cause

`conan.tools.files.copy(pattern, src, dst)` 复制时**保留 pattern 的尾部目录层级**。
当 pattern 写成 `os.path.join("include", "matchit.h")`（即 `include/matchit.h`）且
`dst = os.path.join(package_folder, "include")` 时，实际落盘为
`package_folder/include/` + `include/matchit.h` = `package_folder/include/include/matchit.h`。

该问题与 E217（上游 CMake `install(FILES ... DESTINATION include/<sub>)` 后调
`package_info().includedirs`）是**两个独立根因**：E217 属上游安装目标问题，本候选属
**copy() 自身 pattern 目录语义**，现有知识库未覆盖。

## 方案 / rec_approach

src 与 dst 双侧都 join `include/`，pattern 用裸文件名，使 pattern 无尾部目录：

```python
copy(
    self,
    "matchit.h",
    src=os.path.join(self.source_folder, "include"),
    dst=os.path.join(self.package_folder, "include"),
)
```

若确需按子目录分装（如 include/foo/），则 src 侧指定到该子目录的父目录、dst 保留子目录，
使 pattern 尾部目录与 dst 不重复。

## 验证 / verification

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → 包构建 + test_package 编译运行 exit=0
# → 包目录: package_folder/include/matchit.h（单层）
```

## 适用边界 / affected_scope

- 适用：header-only / 手工 copy 头文件的 Conan 2 配方，pattern 带目录层级 + dst 含同目录名
- 不适用：pattern 无目录（`"*.h"` / `"matchit.h"` 裸文件名）不受影响
- 与 E217 的关系：E217 处理上游 CMake 安装目标，本候选处理 copy() pattern 语义；两者可叠加

## 查重差异

- knowledge/doc/：E217 根因不同（上游 install DESTINATION），未覆盖 copy() pattern 目录保留
- knowledge/graph/index.tsv + E*.kv：引擎查询命中 E217（Phase B: 2）但为部分覆盖
- knowledge/drafts/：无同类草稿
- 新增价值：沉淀 Conan 2 copy() 目录语义这一通用配方陷阱
