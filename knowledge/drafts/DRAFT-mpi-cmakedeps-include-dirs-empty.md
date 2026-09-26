# DRAFT-mpi-cmakedeps-include-dirs-empty — CMakeDeps 给 MPI 的 INCLUDE_DIRS 为空，公开头含 `<mpi.h>` 的包须自行转发

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-26
> **Severity**: medium | **Category**: cmake / cmakedeps / conan / build-system / dependency-missing
> **Audience**: 所有 `requires(MPI)` 且公开头直接 `#include <mpi.h>` 的适配者

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| E216 glib/libxml2 CMakeDeps 组件头文件传播失效 | 已收录 | CMakeDeps 不传播 **components** 的 `INTERFACE_INCLUDE_DIRECTORIES` | E216 是**多组件（components）**路径缺失；本条是**单包无 components** 时 `INCLUDE_DIRS_RELEASE` 直接为空，且对象是 **MPI 包**，症状是消费方 `<mpi.h>` 找不到 |
| DRAFT-conan-cmaketools-transitive-includedirs | 草稿 | CMakeToolchain 的包含目录传递 | 讲 toolchain 侧传递，非 CMakeDeps 生成的数据为空 |
| DRAFT-conan-shared-pkgconfig-requires-drop | 草稿 | shared 形态下 pkg-config Requires 被丢弃 | 属 pkg-config 通道，非 CMakeDeps 通道 |

**查重结论**：对 `open-mpi`（全库 **命中 0 文件**）、`mpich.*INCLUDE_DIRS`、`open-mpi.*INCLUDE_DIRS`、`mpi.h.*找不到`、`package_info.*转发` 检索——除 `mpich` 泛提及（16 文件，均为 Fortran/运行时主题）外，**无任何条目覆盖"MPI 包经 CMakeDeps 生成的 INCLUDE_DIRS 为空"**。**真增量**。

## Scope（何时用）

`requires(...)` 中引入 MPI，且**公开头直接 `#include <mpi.h>`** 的包——并行数值/图计算/求解器类最典型。

触发特征：
- 消费者编译报 `fatal error: 'mpi.h' file not found`；
- 但 MPI 库**链接正常**（libdirs 没坏）→ "库连得上、头找不到"的割裂症状；
- 生成物里 `<pkg>_INCLUDE_DIRS_RELEASE` 为空。

## Symptom

```text
# 消费者编译（含本包公开头，公开头里 #include <mpi.h>）
fatal error: 'mpi.h' file not found

# 生成物里变量为空（缺陷证据）
$ grep -rE "(mpich|open-mpi)_INCLUDE_DIRS_RELEASE" <build>/generators/
  ...  "mpich_INCLUDE_DIRS_RELEASE": "",        ← 空
  ...  "open-mpi_INCLUDE_DIRS_RELEASE": "",     ← 空
```

## Root Cause

制品仓的 `mpich`（实测 5.0.1.2）与 `open-mpi`（实测 5.0.10）经 Conan 2 的
**CMakeDeps** 生成 `<pkg>_INCLUDE_DIRS_RELEASE` 时解析为**空字符串**，于是
`MPI::MPI_C` 这类导入目标的 `INTERFACE_INCLUDE_DIRECTORIES` 为空。

关键点：
1. **缺陷位置是他人归档**（`archives/m/mpich`、`archives/o/open-mpi`）——按
   **SKILL §0.2 铁律**不得越权修改；
2. 因此正确修复位置是**自身包的 `package_info()`**：显式把 MPI 头目录转发给下游；
3. 两种 MPI 实现（mpich / open-mpi）**都踩**，说明是**通用缺陷**而非某实现的偶发。

## Recommended Solution

### 推荐方案（priority 1）— `forward-mpi-includedir-in-package-info`

在自身包 `package_info()` 中，从依赖对象取 MPI 包的实际 `package_folder`，
把其 `include` 追加到 `self.cpp_info.includedirs`：

```python
# 本包公开头直接包含 <mpi.h>，故消费者编译行必须有 MPI 头目录。
# 但 mpich 经 CMakeDeps 生成的 mpich_INCLUDE_DIRS_RELEASE 为空（实测），
# MPI::MPI_C 目标不带 include 目录 → 消费方编译即报 'mpi.h' file not found。
# 该缺陷位于他人归档，按 SKILL §0.2 不越权修改，故在本包侧转发。
mpi_inc = os.path.join(self.dependencies["mpich"].package_folder, "include")
if os.path.isdir(mpi_inc):
    self.cpp_info.includedirs.append(mpi_inc)
```

`os.path.isdir` 守卫避免路径缺失时污染 cpp_info。

### 回退方案（priority 2）— `declare-in-generate-or-report-upstream`

- 若包**不公开** `<mpi.h>`（仅内部使用），可在 `generate()` 注入
  `CMAKE_INCLUDE_PATH`/`CMAKE_PREFIX_PATH`，只解本包；
- 若要从根因修全仓，须按 §0.2 **先获授权**再改 MPI 归档的 `package_info`
  （解全仓，但属跨包改动）。

### 禁止做法

- ❌ 在本 PR 里修改 `archives/m/mpich` 或 `archives/o/open-mpi`（越权，SKILL §0.2）；
- ❌ 让消费方自行加 `-I` 绕过——公开头由本包提供，提供可消费的头是包的**契约责任**。

## 单库实证（2026-09-26）

| 库/版本 | MPI 实现 | 公开头含 `<mpi.h>` 的位置 | 结果 |
|---|---|---|---|
| superlu-dist 9.0.0 | **open-mpi** 5.0.10 | `SRC/include/superlu_defs.h:56` | 转发后消费者编译通过 |
| ptscotch 7.0.12 | **mpich** 5.0.1.2 | `src/libscotch/library_pt.h` | 转发后消费者编译通过 |

两者**独立命中同一缺陷**（不同 MPI 实现），可佐证其为 CMakeDeps 侧的通用问题。

## 测试覆盖边界

- 本条解决的是"**MPI 包 CMakeDeps 元数据不完整 → 消费方缺 `mpi.h`**"的诊断与包侧修法。
- **未**修复 MPI 归档自身的元数据（属根因，需授权后另提）。
- 覆盖边界：验证到"消费方能编译含 `<mpi.h>` 的公开头"为止；**不**覆盖 MPI 运行时行为
  （open-mpi wrapper 的 `OPAL_PREFIX`/`LD_LIBRARY_PATH` 属另一问题层）。

## 关联条目

- 相似：`E216`（Conan CMakeDeps 传播缺陷同族，components 路径）
- 相关：`DRAFT-conan-cmaketools-transitive-includedirs`
