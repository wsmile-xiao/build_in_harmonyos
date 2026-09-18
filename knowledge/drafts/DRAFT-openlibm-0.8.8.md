# DRAFT: 头文件装入 include/<subdir> 导致 test_package 找不到（Makefile 变体）

> 关联 E217（CMake 变体）：`install(FILES ... DESTINATION include/<project>)` 同根因。
> 本草稿补齐 **Makefile 驱动** 的同类场景 —— openlibm 0.8.8 实测。

## 问题

`conan-verify` G2 在 test_package 编译阶段失败：

```
/storage/.../test_package/test.c:17:10: fatal error: 'openlibm.h' file not found
```

## 根因

openlibm 的 `install-headers` 规则把头文件复制到 `$(includedir)/openlibm`（即
`include/openlibm/` 子目录），并与其 `openlibm.pc` 的 `Cflags: -I${includedir}` 一致。
但 conan-init 模板 `package_info()` 默认 `includedirs=["include"]`，不含子目录，
消费者直接 `#include <openlibm.h>` 时解析不到头文件。

## 修复

```python
def package_info(self):
    self.cpp_info.includedirs = ["include/openlibm"]   # 与上游 .pc 的 Cflags 对齐
    self.cpp_info.libs = ["openlibm"]
```

## 验证（openlibm 0.8.8 R01 实测）

- 修复前：`fatal error: 'openlibm.h' file not found`（G2 FAIL）
- 修复后：`conan-verify` G1–G4 全通过，test_package 编译 + ctest 1/1 通过

## 适用范围与边界

- **适用**：任何把头文件安装到 `include/<subdir>` 的库——Makefile `install-headers`
  类规则（本草稿）或 CMake `install(FILES ... DESTINATION include/<project>)`（E217）
- **锚点**：库自带的 `.pc` 文件 `Cflags` 是最可靠的 includedirs 取值来源；
  无 .pc 时读上游安装规则（Makefile 的 includedir/install-headers、CMake 的 DESTINATION）
- **反例**：头文件直接装在 `include/` 根目录的库无需修改（模板默认即可）

## 查重差异（vs E217）

- E217 affected_scope 明确限定"所有 **CMake 工程** 头文件安装到 include/<subdir>"，
  不含 Makefile 项目；本草稿将触发面扩展到**构建系统无关**的通用模式
- 错误签名（`fatal error: '<h>' file not found`）、根因、修复方式与 E217 完全同构；
  若主编认为应合并，建议将 E217 的 affected_scope 扩为"CMake/Makefile 等任何安装规则"，
  本草稿可作为 E217 的补充证据入库

## 关系

- similar_to: E217（CMake 变体，建议合并/扩围）
- prerequisite_of: 无
- caused_by: 无
- conflicts_with: 无

---
*草稿由 openlibm 0.8.8 R01（pc5-11）生成，用于路径 B 知识库扩展 PR*