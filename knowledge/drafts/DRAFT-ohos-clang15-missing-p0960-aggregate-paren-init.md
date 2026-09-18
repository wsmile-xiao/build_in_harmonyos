# DRAFT-ohos-clang15-missing-p0960-aggregate-paren-init — clang15 缺 P0960 聚合括号初始化

> Contributor: 2E77 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-clang15-missing-p0960-aggregate-paren-init`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-ohos-clang15-libcxx-cxx20-capability-gaps` | 已在 main（draft）| clang15+libc++15 的 C++20 能力缺口：**ranges 需实验宏**、特性宏值低于标准、**P1091**（lambda 捕获结构化绑定）| 同属"clang15 缺 C++20 特性"族，但**覆盖的特性不同**：该条讲 ranges 宏与 P1091（处置=改判特性宏 / 拷贝绑定），本条讲 **P0960**（处置=**为聚合补显式 ctor**）。实测该条全文 `P0960` / `construct_at` / `括号初始化` 命中 **0** |
| `DRAFT-libcxx15-missing-cpp20-atomic-ref` / `-spaceship` | 已在 main（draft）| libc++15 **库侧**缺 C++20 组件（atomic_ref / spaceship）| 那是**库实现缺失**（换/补实现）；本条是**编译器前端特性缺失**（改源码构造方式）|
| `DRAFT-ohos-libcxx15-missing-cpp20-ranges-algorithms` 等 | 已在 main（draft）| ranges 算法族缺失 | 同族不同特性 |

**全库查证**：对 `P0960` / `construct_at` / `聚合括号初始化` / `parenthesized
aggregate` / `no matching function for call to 'construct_at'` 等关键词，在
`knowledge/index.tsv`、`knowledge/graph/index.tsv`、`knowledge/graph/*.kv`、
`knowledge/doc/*.md`、`knowledge/drafts/*.kv`、`knowledge/drafts/*.md` 中 grep ——
**命中 0 条**（仅本条目自身与同批草稿的交叉引用）。

> 粒度说明：本仓对 libcxx/clang15 缺口族一贯**细粒度独立成条**（现有 50 份相关
> 草稿，`missing-cpp20-atomic-ref` 与 `missing-cpp20-spaceship` 即各自独立），
> 本条目遵循同一惯例。

## Scope（何时用）

OHOS clang15 上构建、对**聚合类型**（无用户声明构造函数的 struct/class）使用
**圆括号式初始化**的 C++20 项目。

高频触发点：

```cpp
std::vector<Agg> v;
v.emplace_back(1, 2.0);              // ← 最常见
auto p = std::make_unique<Agg>(1);   // ← 同样触发
std::construct_at(ptr, 1, 2.0);      // ← 直接调用
```

## Symptom

报错落在 **libc++ 头文件内部**，而不是用户代码行：

```console
libcxx-ohos/include/c++/v1/__memory/allocator_traits.h:298:9:
  error: no matching function for call to 'construct_at'
        _VSTD::construct_at(__p, _VSTD::forward<_Args>(__args)...);
        ^~~~~~~~~~~~~~~~~~~
note: in instantiation of function template specialization
      'std::allocator_traits<std::allocator<BackslashCommand>>::construct<...>'
      requested here
note: in instantiation of ... 'std::vector<BackslashCommand>::__construct_one_at_end<...>'
```

> ⚠️ 报错位置在标准库头里是**症状落点**，容易误判为 libc++ 缺陷或工具链损坏。

## Root Cause

C++20 的 **P0960**（Paren-init of aggregates）允许用圆括号直接初始化聚合：
`Agg x(1, 2.0)`。该特性 **Clang 16 才实现**，OHOS 的 clang 15 尚未支持。

**关键实测结论**：`-std=c++20` 与 `-std=c++2b` **同样失败** —— 这是编译器前端
特性实现问题，**与 `-std` 取值无关**（升标准版本不会解决）。

## Recommended Solution

### 主方案（priority 1）— 为聚合补显式构造函数

```cpp
struct BackslashCommand
{
    CommandCategory mCategory;
    std::string_view mCommand;
    std::string_view mCommandWithArg;
    std::string_view mDesc;
    std::function<void(std::string_view arg)> mFunc;

    // clang15 未实现 P0960：补显式 ctor 后，既有花括号初始化列表与
    // emplace_back 均可工作
    BackslashCommand(CommandCategory c, std::string_view cmd,
                     std::string_view cmdWithArg, std::string_view desc,
                     std::function<void(std::string_view)> f)
        : mCategory(c), mCommand(cmd), mCommandWithArg(cmdWithArg),
          mDesc(desc), mFunc(std::move(f))
    {
    }
};
```

**为何补 ctor 而非改写调用点**：调用点可能有十几处（cif-tools 实测 8 处
`emplace_back`），补一处 ctor 即可全解。

**补 ctor 前必须确认**：该类型**没有指定初始化器**用法，否则会破坏它
（designated initializers 要求类型仍是聚合）：

```bash
grep -rnE "<TypeName>[^(]*\{[^}]*\.[a-zA-Z_]+\s*=" <src>/
```

> 同源先例：libcifpp/10.0.4 的 `_patch_aggregate_ctors`（为 `virtual_table` /
> `virtual_cursor` 补 ctor）即此思路。

### 回退方案（priority 2）— 改写调用点为花括号

若不能改类型定义（公共头影响面过大、或确有指定初始化器用法）：

```cpp
v.emplace_back(1, "x");   →   v.push_back(B{1, "x"});
std::make_unique<B>(1)    →   std::make_unique<B>(B{1})
```

缺点是逐站点改写（本次 8 处），可读性略降。

### 禁止做法

- ❌ 把报错归因于 libc++ / 标准库缺陷 —— 那只是症状落点，真因在编译器前端；
- ❌ 以为升 `-std=c++2b` 可解 —— 实测同样失败。

## 实测证据（2026-09-16，cif-tools 2.0.0）

| 项 | 结果 |
|---|---|
| 触发点 | `src/mmcql.cpp` 的 `gBackslashCommands.emplace_back(...)`（**8 个站点**）|
| 报错 | `allocator_traits.h:298: no matching function for call to 'construct_at'`，级联 `vector::__construct_one_at_end` |
| 标准探针 | `-std=c++20` 与 `-std=c++2b` **均失败**（证明非标准版本问题）|
| 处置 | 为 `BackslashCommand` 补显式构造函数（5 参数）|
| 结果 | `construct_at` 报错全部消除；`conan create` 编译错误计数 14 → **0**；exit=0、test_package PASS |

## 测试覆盖边界

本条只处理**编译器前端缺 P0960** 导致的聚合括号初始化失败。区分相邻情形：

- libc++ **库侧**缺组件（atomic_ref / spaceship）→ `DRAFT-libcxx15-missing-cpp20-*`；
- ranges 算法/视图缺失 → `DRAFT-ohos-libcxx15-missing-cpp20-ranges-algorithms` 等；
- lambda 捕获结构化绑定（P1091）→ `DRAFT-ohos-clang15-libcxx-cxx20-capability-gaps`。

四者同族但特性与处置互不相同。

## 关联条目

- 相似：`DRAFT-ohos-clang15-libcxx-cxx20-capability-gaps`（ranges 宏 + P1091）、
  `DRAFT-libcxx15-missing-cpp20-atomic-ref`、`DRAFT-libcxx15-missing-cpp20-spaceship`
- 差异：见上方差异化定位表
