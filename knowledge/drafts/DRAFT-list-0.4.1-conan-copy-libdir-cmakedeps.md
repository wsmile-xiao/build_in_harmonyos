# DRAFT-list-0.4.1-conan-copy-libdir-cmakedeps

> Contributor: pc2-13 | Status: Draft | Updated: 2026-09-18
> Source: list 0.4.1 HarmonyOS PC Path B adaptation (task list-0.4.1-r01-pc2-13)
> 对应 KV: knowledge/drafts/DRAFT-list-0.4.1-conan-copy-libdir-cmakedeps.kv

## 主题 / 触发场景

Conan 2 配方 `package()` 中，raw-Makefile 库（无 configure）的产物带
中间目录层（`build/libxxx.a`、`src/xxx.h`）。若直接用
`copy(self, "build/libxxx.a", self.source_folder, package/lib)`，
落盘为 `package/lib/build/libxxx.a`；头文件落盘为
`package/include/clibs/src/list.h`。CMakeDeps 只搜索 `lib/`、`include/`，
test_package 的 `find_package(list)` 在**库侧**报
`Library 'clibs_list' not found in package`（cmakedeps_macros.cmake），
configure 阶段失败（`conan create` G2 FAIL）。

## 与既有知识差异（七轴查重摘要）

- DRAFT-matchit-r01-conan-copy-pattern-dir-keep 与 DRAFT-gulrak 均覆盖
  **include 侧头文件**双层嵌套（`include/include/xxx.h` → `file not found`）；
  本草稿新增 **lib 侧**（`lib/build/libxxx.a`）与 **build/、src/ 中间层级**
  场景及 CMakeDeps **"Library not found in package"** 错误面（matchit/gulrak
  未覆盖，错误特征不同）。
- 同类根因：`conan.tools.files.copy` 会保留 pattern 的尾部目录层级。

## 现象 / error_signature

```text
CMake Error at build/.../generators/cmakedeps_macros.cmake:81 (message):
  Library 'clibs_list' not found in package.  If 'clibs_list' is a system
  library, declare it with 'cpp_info.system_libs' property
Call Stack: list-Target-release.cmake ... conan_package_library_targets
```

包目录实测（错误态）：

```text
package_folder/lib/build/libclibs_list.a    # ← lib/ 下一级多出 build/
package_folder/include/clibs/src/list.h      # ← include/clibs/ 下一级多出 src/
```

## 根因

`conan.tools.files.copy(pattern, src, dst)` 的 pattern 含目录（如
`build/libclibs_list.a`）时，复制保留该尾部目录；basic_layout 下
build_folder 与 source_folder 分离，Makefile 产物位于 source_folder/build/。
若 dst 只指向 package 的 lib/，落盘为 `lib/build/…`，而 CMakeDeps 生成的
`-L` 路径仅含 `lib/`，无法定位库文件 → `conan_package_library_targets`
报 "Library not found in package"。

## 修复（rec_approach: copy-src-dst-symmetric-join）

`copy()` 的 src 精确 join 到产物所在**子目录**，dst 精确到包内目标目录，
pattern 用裸文件名（对称 join，消除中间层）：

```python
from conan.tools.files import copy
import os

def package(self):
    # 库文件：src 指向 source_folder/build，pattern 裸名
    copy(self, "libclibs_list.a",
         os.path.join(self.source_folder, "build"),
         os.path.join(self.package_folder, "lib"))
    # 头文件：src 指向 source_folder/src，pattern 裸名
    copy(self, "list.h",
         os.path.join(self.source_folder, "src"),
         os.path.join(self.package_folder, "include", "clibs"))
```

修复后包目录：

```text
package_folder/lib/libclibs_list.a
package_folder/include/clibs/list.h
```

## 验证

- 修复前：`conan create` G2 FAIL（test_package find_package 报 Library not found）
- 修复后：`ohc-run.py conan-verify list 0.4.1` → **G1-G4 全 PASS**，test_package
  双用例（test_consumer/test_ohos）编译链接运行通过
- 日志：archives/l/list/0.4.1/reports/conan-create.log（G2 段）、conan-verify-report.md

## 适用边界

- **适用**: 产物目录带中间层的 raw-Makefile / 非标准布局库的 Conan 2 package()；
  copy 保留 pattern 尾部目录的语义对所有 Conan 2 配方通用
- **不适用**: 上游 CMake 已用 `install(TARGETS DESTINATION lib)` 正规安装的库
  （由 E217/E221 等覆盖）；include 侧同类问题 → DRAFT-matchit
- **反例**: 若 package() 用 `autotools.install()`/`cmake.install()` 而非 copy，
  无此问题

## 查重差异结论

- `similar_to`: DRAFT-matchit-r01-conan-copy-pattern-dir-keep,
  DRAFT-gulrak-filesystem-1.5.8-headeronly-copy-nested-include
- `caused_by`: basic_layout（build/source 分离）+ raw-Makefile 产物目录结构
- `prerequisite_of`: conan-verify G2 PASS / test_package find_package
- `conflicts_with`: 无
- 新增差异：lib 侧 + build/src 中间层级 + CMakeDeps library-not-found 错误面