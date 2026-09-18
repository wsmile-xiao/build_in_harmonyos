# DRAFT-ohos-conandata-patches-silently-unapplied — 声明了补丁却没应用（静默不生效）

> Contributor: 8F02 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-conandata-patches-silently-unapplied`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E282` | 图谱 | `conandata.yml` 补丁的 `base_path` 定位错（多源/嵌套源码下补丁打到了错误根）| 那是"应用了但**找错根**"；本条是"**压根没应用**" |
| `E515` / `E526` | 图谱 | `strip=0` / `a/ b/` 前缀 / git-style 补丁的 strip 层级与 patch-ng 语义 | 同属"应用了但**打不对**"；本条是应用环节整体缺失 |
| `E254` | 图谱 | 用 `export_sources()` + `export_conandata_patches` **新增源码文件**（不走补丁）| 那是主动选择"不写补丁"；本条是**写了补丁却漏调用应用函数** |
| `DRAFT-ohos-perl-script-package-conan-adaptation` | 草稿 | 顺带提一句"在 build() 里自校首行是否真被改写（防补丁静默失效）" | 仅一句附带提醒，**未展开机制**；本条是专门条目 |

**全库查证**：对 `apply_conandata_patches` + `静默` / `未调用` / `forgot` /
`never applied` 等组合关键词 grep —— 除上表（机制均不同）外**命中 0 条**
专讲"声明了但未调用应用函数"的条目。

## Scope（何时用）

任何用 `conandata.yml` 的 `patches:` 声明补丁的 Conan 2 配方。

**高危场景**：从 autotools 范式（`apply_conandata_patches` 习惯性写在 `build()`
开头）切换到新写 CMake 或自定义配方时，容易整段漏掉——补丁文件都写好了、
`conandata.yml` 也声明了，只差配方里那一行调用。

## Symptom

**没有任何报错**，只是构建行为与完全不打补丁**一模一样**。

实测 cif-tools 2.0.0：

```console
$ grep '^CXX_FLAGS' CMakeFiles/prmain.dir/flags.make
CXX_FLAGS = -stdlib=libc++ -std=c++20 -fexperimental-library -O3 -DNDEBUG -std=c++17
                                                                    ^^^^^^^^^ 补丁本应把这个改掉
```

补丁文件明明存在（`patches/0001-cmake-cxx-standard-20.patch`），`conandata.yml`
也声明了它，但 `CMakeLists.txt` 从未被改。

> ⚠️ 最坏的地方：**误诊方向**。因为没有报错、补丁目录也"看起来齐全"，很容易
> 判断成"补丁内容写错了"，于是反复重写 `.patch` —— 但方向错了，怎么改都不会生效。

## Root Cause

Conan 2 的补丁应用**不是自动的**，需两个独立步骤：

| 步骤 | 位置 | 作用 |
|---|---|---|
| ① `export_conandata_patches(self)` | `export_sources()` | 把补丁文件纳入配方导出源 |
| ② `apply_conandata_patches(self)` | `build()`（configure 前）| **按序应用**补丁 |

`conandata.yml` 的 `patches:` 列表只是**声明**。缺任一步都**不报错**：
补丁照旧被导出（文件在 `conandata.yml` 里，`export_sources` 缺失时也可能因
其他机制可见），但构建时根本没使用。

## Recommended Solution

### 主方案（priority 1）— 补全两个钩子 + 反证生效

```python
def export_sources(self):
    export_conandata_patches(self)

def build(self):
    apply_conandata_patches(self)      # 必须在 configure 之前
    cmake = CMake(self)
    cmake.configure()
    cmake.build()
```

**顺序要求**：若补丁改的是 `CMakeLists.txt`，`apply` 必须在 `cmake.configure()`
**之前**——否则 configure 已按旧文件生成了缓存，补丁再应用也只影响源码树。

**加一步自校**（防将来重构又静默退回）：断言补丁的目标变化确实出现，例如

```python
# 断言补丁真的生效（flags.make 里不再有 -std=c++17）
```

### 回退方案（priority 2）— source() 内联替换

若补丁只是一两行纯文本替换、且希望免去整条补丁链路，可在 `source()` 内直接
读写替换。**代价**：绕过 `patches/` 目录的审计（R8/PF5 平台宏闸不再覆盖此处），
故仅适用于**非平台宏的机械替换**，并须在 `notes.md` 说明理由。

### 禁止做法

- ❌ 在补丁未生效时反复重写 `.patch` 内容——先确认 `apply_conandata_patches`
  是否被调用，再判断补丁内容对错；
- ❌ 只写 `export_sources()` 或只写 `patches:` 就以为补丁会自动应用。

## 实测证据（2026-09-16，cif-tools 2.0.0）

| 项 | 结果 |
|---|---|
| 初版配方 | `conandata.yml` 声明了 2 个补丁，但配方内**无** `apply_conandata_patches` / `export_sources` |
| 症状 | `CXX_FLAGS` 末尾始终 `-std=c++17`（补丁应改为 c++20），编译期报 libcifpp 头文件错——**与未打补丁完全一致** |
| 误诊成本 | 期间多轮重写补丁内容（含 0002 的 fmt 替换、P1091/P0960 处置），均无效果 |
| 修复 | 补 `export_sources()` + `build()` 内 `apply_conandata_patches(self)` |
| 修复后 | `-std=c++17` 消失；旧错误计数由 14 → **0**；`conan create` exit=0、test_package PASS |

## 测试覆盖边界

本条只处理"**声明了却未应用**"。区分相邻情形：

- 应用了但根目录/层级错 → `E282` / `E515` / `E526`；
- 主动选择不写补丁、改走 `export_sources` 新增文件 → `E254`。

## 关联条目

- 相似：`E282`、`E515`、`E526`（应用了但打不对）、`E254`（改走新增文件）
- 差异：见上方差异化定位表
