# DRAFT-gulrak-filesystem-1.5.8-headeronly-copy-nested-include — header-only 库 package() 复制嵌套 include 子目录失败

> **Contributor**: pc1-14 | **Status**: DRAFT | **Updated**: 2026-09-06
> **Severity**: medium | **Category**: conan / packaging / header-only
> **Audience**: 适配头文件位于 `include/<subdir>/` 布局的 header-only 库的配方编写者

## 问题签名与触发条件

问题签名：

```text
Imported target "xxx::xxx" includes non-existent path
  "/.../.conan2/p/b/xxxxx/p/include"
in its INTERFACE_INCLUDE_DIRECTORIES
CMake Generate step failed. Build files cannot be regenerated correctly.
ERROR: xxx (test package): Error in build() method ... cmake.configure()
```

或 package() 阶段直接出现：

```text
package(): WARN: No files in this package!
```

触发条件：header-only 库源码树的公共头不在根目录直属，而在 `include/<subdir>/`
（例如 gulrak-filesystem 的 `include/ghc/*.hpp`、上游习惯的 `include/<lib>-<version>/`），
配方 package() 若用 `copy(self, "*.hpp", src=..., dst=...)` 这类只匹配根目录直属文件的模式，
将复制 0 个文件。

## 根因（两因叠加）

1. **conan copy() 的 pattern 匹配不跨子目录**：`conan.tools.files.copy()` 对 src 树做
   `os.walk` 后按**相对路径** fnmatch（copy_pattern.py 的 `_filter_files`）。
   `*.hpp` 只命中 src 根直属 `.hpp`，`include/ghc/*.hpp` 的相对路径带 `/`，不匹配。
2. **layout/no_copy_source 对 source_folder 的影响**：header-only 配方常见
   `no_copy_source = True`；若再定义 `layout(): basic_layout(self)`（内部
   `folders.source = "."`），package() 里 `self.source_folder` 语义偏离"共享源码目录"的
   直觉。加上 `dst="include"` 这类相对路径依赖 package_folder 计算，肉眼难以核对落位。

结果：包内 `include/` 不存在（或为空），CMakeDeps 生成的
`INTERFACE_INCLUDE_DIRECTORIES=<package>/include` 指向不存在的目录，
test_package 在 `cmake.configure()` 阶段直接失败 → G2 FAIL。

## 解决方案（子目录感知复制 + 显式 package_folder 落位）

```python
def package(self):
    # 保留相对路径复制 include/ghc/*.hpp → package include/ghc/*.hpp
    copy(self, "ghc/*.hpp",
         src=os.path.join(self.source_folder, "include"),
         dst=os.path.join(self.package_folder, "include"))
    copy(self, "LICENSE*", src=self.source_folder,
         dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
```

要点：

- pattern 写子目录前缀（`ghc/*.hpp`），`keep_path` 默认 True 保留 `ghc/` 前缀；
- `dst` 一律 `os.path.join(self.package_folder, ...)` 绝对路径，不要写裸 `"include"`；
- 无编译阶段的 header-only 配方不需要 `layout()`（移除 basic_layout，避免其
  `folders.source="."` 与 `no_copy_source` 源码目录语义互相干扰）；
- `conandata.yml` 填官方 URL + 真实 sha256；`package_type = "header-library"`；
- 排障时用 `conan create -vdebug`，`copy(pattern=...) copied N files` 可核对复制计数。

## 验证（gulrak-filesystem 1.5.8 实测）

- 修复前：`conan create`（ohos-aarch64 profile）G2 FAIL，
  `package(): WARN: No files in this package!`，Imported target 引用不存在的 `p/include`。
- 修复后：`conan create` EXIT=0，包内含 6 个头文件（`include/ghc/*.hpp`）+ `licenses/LICENSE`；
  `conan-verify` G1-G4 / L2 / L4 / L5 全部 PASS；test_package 消费者测试 16/16 通过。
- 证据日志：`archives/g/gulrak-filesystem/1.5.8/reports/conan-create.log`、
  `reports/conan-verify-report.md`、`reports/test-report.md`。

## 适用边界与反例

- **适用**：所有 header-only C/C++ 库（doctest/catch2 型 cpp_info 仅头文件），
  头文件位于 `include/<subdir>/` 的常见布局。
- **反例/不适用**：头文件直接在 `include/` 根（无子目录）时 `*.hpp` 模式即可命中，
  不受本问题影响；有编译产物的库不涉及 package() 纯复制路径。
- 与 `DRAFT-concurrencpp-0.1.7-cmake-header-install-subdir` 的区别：concurrencpp 草稿
  根因是"上游 CMake install 到 include/<subdir> + INSTALL_INTERFACE 未导出 → 消费者
  includedirs 不匹配"，解决点在 `package_info().includedirs` 声明；本候选根因是
  "conan copy() pattern 不跨子目录 + layout/no_copy_source 语义"，解决点在
  `package()` 的复制模式与落位。触发面（G2/test_package）部分重叠，方案不同。

## 关系字段

- `causes`: DRAFT-concurrencpp-0.1.7-cmake-header-install-subdir（同类 header-only include 路径问题）
- `similar_to`: DRAFT-concurrencpp-0.1.7-cmake-header-install-subdir
- `caused_by`: []  `conflicts_with`: []  `prerequisite_of`: []
