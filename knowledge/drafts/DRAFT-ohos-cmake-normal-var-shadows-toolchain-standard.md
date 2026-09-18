# DRAFT-ohos-cmake-normal-var-shadows-toolchain-standard — 上游普通变量压掉配方注入的 C++ 标准

> Contributor: 4D18 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-cmake-normal-var-shadows-toolchain-standard`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E096` | 图谱 | CMake 在 OHOS 上**检测不到**编译器 C++ 标准能力（"System is unknown to cmake"），需**显式设置** `CMAKE_CXX_STANDARD` 绕过检测 | 那是"没设/设不上"；本条是"**设了却被上游覆盖**"——两条的处置方向相反：E096 加显式设置即可，本条必须改上游源码。实测 E096 全文 `tc.variables`/`覆盖`/`末尾追加` 命中 0 |
| `E006` 等 CMake 工具链条 | 图谱 | OHOS CMake 工具链/ABI 检测族问题 | 机制不同（工具链识别 vs 变量作用域遮蔽）|

**全库查证**：对 `CMAKE_CXX_STANDARD` + `tc.variables` / `普通变量覆盖` /
`末尾追加 -std=` / `flags.make` 等组合关键词，在 `knowledge/index.tsv`、
`knowledge/graph/index.tsv`、`knowledge/graph/*.kv`、`knowledge/doc/*.md`、
`knowledge/drafts/*.kv`、`knowledge/drafts/*.md` 中 grep —— 除 `E096`（机制相反）外**命中 0 条**。

## Scope（何时用）

CMake 工程满足两个条件：

1. 上游 `CMakeLists.txt` 用**普通变量**固定标准：`set(CMAKE_CXX_STANDARD 17)`；
2. 本项目需要的标准**高于**上游设定（常见于"上游钉 C++17、但其依赖的新版头文件要 C++20"）。

实测实例（cif-tools 2.0.0 + libcifpp 10.0.4）：

```
cif-tools/CMakeLists.txt:43   set(CMAKE_CXX_STANDARD 17)   ← 普通变量
libcifpp/10.0.4 的 item.hpp 用 concept / std::remove_cvref_t ← 需 C++20
```

## Symptom

**症状一：依赖头文件大面积报错**（真正原因被掩盖）

```console
include/cif++/item.hpp:85:  error: unknown type name 'concept'
include/cif++/item.hpp:176: error: no template named 'remove_cvref_t' in namespace 'std'
include/cif++/item.hpp:353: error: unknown type name 'FloatType'
```

**症状二：实际生效的标志与配方意图不符**（决定性证据）

```
$ grep '^CXX_FLAGS' CMakeFiles/prmain.dir/flags.make
CXX_FLAGS = -stdlib=libc++ -std=c++20 -fexperimental-library -O3 -DNDEBUG -std=c++17
                                                                    ^^^^^^^^ 末尾追加，胜出
```

## Root Cause

CMakeToolchain 用 **cache 变量**传递标准；上游在子 scope 用**普通变量**重新赋值，
普通变量**遮蔽**同名 cache 变量，CMake 按它生成 `-std=c++17` 并**追加到命令行末尾**。

### 两个看似合理、实测均无效的修法

| 尝试 | 结果 |
|---|---|
| `tc.variables["CMAKE_CXX_STANDARD"] = "20"` | ❌ 被上游普通变量覆盖，`CXX_FLAGS` 仍为 `-std=c++17` |
| `tc.extra_cxxflags.append("-std=c++20")` | ❌ 被末尾追加的 `-std=c++17` 压掉（顺序在后者胜出）|
| 同上一并加进 `extra_cflags` | ❌ **更糟**：C 编译器报 `invalid argument '-std=c++20' not allowed with 'C'`，configure 阶段直接失败 |

## Recommended Solution

### 主方案（priority 1）— patch 上游那一行

```diff
-set(CMAKE_CXX_STANDARD 17)
+set(CMAKE_CXX_STANDARD 20)
```

作为 portability 补丁提交（`patch_type: "portability"`）。这是**唯一**能真正改变
编译标志的修法。

**注意两点**：

1. 上游**子目标可能有另一处独立设置**——如测试子目录的 `CMakeLists.txt` 自己写
   `target_compile_features(... cxx_std_NN)` 或再 `set(CMAKE_CXX_STANDARD)`，
   根文件改了就以为全生效是错的。先枚举：

```bash
grep -rn "CMAKE_CXX_STANDARD\|cxx_std_" <src>/CMakeLists.txt <src>/*/CMakeLists.txt
```

2. `set(CMAKE_CXX_STANDARD_REQUIRED ON)` 无需改动，保持上游语义即可。

### 回退方案（priority 2）— 改写生成的 flags.make

仅当补丁路径确实不可行时使用：configure 之后直接改 build 目录的 `flags.make`。
**脆弱**——绕过 CMake 依赖跟踪，重新 configure 即失效，必须在 `notes.md` 写明。

### 禁止做法

- ❌ 只写 `tc.variables[...]` 或用 `extra_cxxflags` 就认为修好——会被压掉；
- ❌ 把 `-std=c++20` 加进 `extra_cflags`——C 编译器拒绝，configure 直接失败。

## 实测证据（2026-09-16，cif-tools 2.0.0）

| 项 | 结果 |
|---|---|
| 上游写法 | `CMakeLists.txt:43  set(CMAKE_CXX_STANDARD 17)` + `:44 ..._REQUIRED ON` |
| 实测 CXX_FLAGS | 末尾 `-std=c++17`（配方已注入 `-std=c++20` 与 `-fexperimental-library`）|
| 修法对比 | `tc.variables` 无效；`extra_cxxflags` 无效；`extra_cxxflags`+`extra_cflags` 致 configure 失败 |
| 补丁后 | `-std=c++17` 消失，libcifpp 头文件的 concept/remove_cvref_t/FloatType 报错全部消除 |
| 处置 | 补丁 `0001-cmake-cxx-standard-20.patch`（portability）|

## 测试覆盖边界

本条只处理"**上游普通变量覆盖 + 末尾追加**"这一机制。区分相邻情形：

- CMake **检测不到**标准能力（需显式指定）→ `E096`；
- 上游声明 `target_compile_features(... cxx_std_23)` 而工具链不支持 c++23 →
  那是"要求值不可达"，处置是降到受支持的标准（同源包 libcifpp 的做法）。

## 关联条目

- 相似：`E096`（机制相反：检测失败 → 需显式设置）
- 差异：见上方差异化定位表
