# cif-tools 2.0.0 适配笔记

## 概述

cif-tools 是 PDB-REDO 出品的 mmCIF / PDB 文件处理工具集，提供 6 个命令行程序：
`pdb2cif`、`cif2pdb`、`cif-diff`、`cif-merge`、`cif-validate`、`mmcql`。

- 上游：https://github.com/PDB-REDO/cif-tools
- 版本：2.0.0（tag `v2.0.0`，注意带 `v` 前缀）
- 构建系统：CMake（≥3.23）
- 许可：BSD-2-Clause
- 编译日期：2026-09-16
- 状态：built（`conan create` exit=0，test_package PASS）

## 依赖

| 依赖 | 必要性 | 说明 |
|---|---|---|
| `libcifpp/10.0.4` | 必需 | `find_package(cifpp 10)`，主版本必须为 10；v9.0.6 不满足 |
| `libmcfp/1.4.2` | 必需 | `find_package(mcfp)`；缺则上游回退 CPM 联网拉取（CI 禁网）|
| `mrc/1.3.17` | 可选 | `find_package(mrc QUIET)`，缺则 `USE_RSRC=FALSE`；ohpcd 已发布故引入 |

> `readln` 是 tarball 内 vendored 的子库（`readln/readln.cpp`），非外部依赖。

### 消费者契约：CMake 名 ≠ conan 包名

上游按 `find_package(cifpp)` / `cifpp::cifpp` 引用依赖，但发布包只设了
`pkg_config_name=cifpp`（未设 `cmake_file_name`/`cmake_target_name`），CMakeDeps
默认会生成 `libcifpp-config.cmake` → 上游找不到。故配方在 `generate()` 内做别名：

```python
deps = CMakeDeps(self)
deps.set_property("libcifpp", "cmake_file_name", "cifpp")
deps.set_property("libcifpp", "cmake_target_name", "cifpp::cifpp")
deps.set_property("libmcfp",  "cmake_file_name", "mcfp")
deps.set_property("libmcfp",  "cmake_target_name", "mcfp::mcfp")
```

（`mrc` 配方的 recipe 已设 `cmake_file_name=mrc`，无需覆盖。）

## 源码修改（2 个补丁，均 portability）

### 补丁 0001：CMakeLists.txt 的 C++ 标准 17 → 20

**现象**：libcifpp/10.0.4 的头文件在 C++17 下大面积报错：

```
include/cif++/item.hpp:85: error: unknown type name 'concept'
include/cif++/item.hpp:176: error: no template named 'remove_cvref_t' in namespace 'std'
include/cif++/item.hpp:353: error: unknown type name 'FloatType'
```

**根因（实测）**：上游 `CMakeLists.txt:43` 用**普通变量** `set(CMAKE_CXX_STANDARD 17)`。
普通变量会覆盖 CMakeToolchain 注入的同名 cache 变量，CMake 因而在编译命令行
**末尾追加 `-std=c++17`**：

```
CXX_FLAGS = -stdlib=libc++ -std=c++20 -fexperimental-library -O3 -DNDEBUG -std=c++17
                                                                              ^^^^^^^^ 后者胜出
```

> ⚠️ 此处走过两条弯路，均已证伪：
> ① `tc.variables["CMAKE_CXX_STANDARD"]="20"` → 被上游普通变量覆盖，无效；
> ② 把 `-std=c++20` 同时加进 `extra_cxxflags` 与 `extra_cflags` → C 编译器报
> `invalid argument '-std=c++20' not allowed with 'C'`（TryCompile 阶段失败）。
>
> **结论：唯一可靠修法是 patch 上游该行**（与同源包 libcifpp 的 C++20 口径一致）。

### 补丁 0002：std::format → fmt::format 等三处 clang15 兼容

**① `std::format` 链接期缺符号**（2 处，`src/mmcql.cpp`）

```
ld.lld: error: undefined symbol: typeinfo for std::__n1::format_error
         >>>> referenced by std::__n1::__throw_format_error
```

OHOS libc++15 的 `std::format` **能编译但无法链接**（libc++.so 内无 format_error
实现；`-fexperimental-library` 只让头文件暴露 API）。按站点替换为 `fmt::format`，
并改用 `#include <fmt/format.h>`——`fmt` 由 libcifpp 以 `transitive_headers/libs`
传递，其 `cpp_info` 已带 `FMT_HEADER_ONLY=1`（header-only，无需额外链接 fmt 库）。

**② `readln/readln.cpp` 的 `std::format`（1 处）→ 纯 stdlib**

该处仅为整数拼接（`"\x1b[{}G"`），而 `readln` 是独立 CMake 目标
（`CMakeLists.txt:135-137`，只加自己的 include 目录、**不链接 `cifpp::cifpp`**），
拿不到 fmt 的头路径（实测 `fatal error: 'fmt/format.h' file not found`）。
故改为 `"\x1b[" + std::to_string(pos + 1) + "G"`，彻底免掉该目标的 fmt 依赖。

**③ clang15 未实现的两个 C++20 特性**（各 1 处，`src/mmcql.cpp`）

实测二者在 `-std=c++20` 与 `-std=c++2b` 下**都失败**（属 Clang 16 才实现）：

| 特性 | 报错 | 处置 |
|---|---|---|
| P1091 lambda 捕获结构化绑定 | `'cat' in capture list does not name a variable` | 先复制到具名变量 `const auto category = cat;` 再捕获 |
| P0960 聚合的括号式初始化 | `no matching function for call to 'construct_at'`（`gBackslashCommands.emplace_back(...)` 8 处站点）| 为 `BackslashCommand` 补显式构造函数（花括号初始化列表与 `emplace_back` 均可工作）|

> P0960 的处置方式与同源包 libcifpp 的 `_patch_aggregate_ctors` 同思路（补 ctor）。

### 另一个静默失效坑（值得记住）

补丁最初**完全不生效**，且**不报任何错**：配方在 `conandata.yml` 声明了
`patches:` 却未调用 `apply_conandata_patches(self)`——补丁被导出却永不应用。
症状是构建行为与未打补丁一模一样（实测 `CXX_FLAGS` 仍为 `-std=c++17`）。
补上 `export_sources()` + `build()` 内的 `apply_conandata_patches(self)` 后即修复。

## 上游测试

**上游 2.0.0 未提供测试**：`CMakeLists.txt` 的 `if(BUILD_TESTING)` 整块被注释掉
（源码实测确认），无 ctest、无测试源文件。属"上游未提供"，**非环境不可用**，如实申报。

## test_package（消费者视角，真实执行）

`test_package/src/test_cif_tools.sh` 三项断言：

1. **6 个可执行文件齐全**（`pdb2cif` / `cif2pdb` / `cif-diff` / `cif-merge` /
   `cif-validate` / `mmcql`）；
2. **6 个工具 `--version` 均成功执行（rc=0）** —— 这是本包最有价值的断言：
   工具为**动态链接**，能运行即证明其全部共享库依赖（libcifpp / libmcfp / fmt 等）
   在运行环境中可解析。实测该断言成功揪出过 `libfmt.so.7` 缺失
   （`Error loading shared library libfmt.so.7`）；
3. **6 个工具 `--help` 均输出用法文案**（证明进入真实主流程）。

刻意**不做**真实 CIF 解析断言，理由均实测：

- `cif-validate` / `mmcql` 解析需 `mmcif_pdbx.dic` 字典，**该字典不在包内**
  （实测 `Could not load dictionary mmcif_pdbx.dic`，rc=1）；
- `cif-diff` 传两个文件会**启动 Vim 分页器**（实测 rc=124 挂起，
  `Vim: Warning: Output is not to a terminal`）——CI 沙箱无 TTY，不可作断言。

## 验证结果

```
conan create archives/c/cif-tools/2.0.0 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
→ exit=0；编译错误 0；6 个目标全部 Built
→ Package created
→ test_package PASS
```

## 交付物

- `bin/pdb2cif`、`bin/cif2pdb`、`bin/cif-diff`、`bin/cif-merge`、
  `bin/cif-validate`、`bin/mmcql`
- `share/man/man1/*.1`（上游安装的手册页）

## 注意事项

1. **C++ 标准必须 patch 上游 CMakeLists**：普通变量会覆盖 toolchain 变量并追加
   `-std=c++17`，仅靠配方注入 flags 无效。
2. **不要把 `-std=c++20` 加进 `extra_cflags`**：C 编译器会拒绝（TryCompile 失败）。
3. **`-fexperimental-library` 必需**：`std::format` 与 `std::ranges` 在 OHOS libc++15
   上均需该开关才暴露 API（实测 `std::ranges::sort` 无开关时
   `no type named 'sort' in namespace 'std::ranges'`）。
4. **conandata 声明补丁后务必调用 `apply_conandata_patches`**，否则静默失效。
5. 新增/修改补丁时遵守 R8：不得引入平台条件编译宏，用无条件定义或上游兼容写法。
