# DRAFT-sole-1.0.4-thread-local-non-trivial-destruction — `__thread` 用于非平凡析构/非常量初始化类型在 clang 15 下编译失败

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-19
> **Severity**: 🟡 medium | **Category**: compat / compiler / tls / cpp

## 问题现象

clang 15（含 HarmonyOS PC aarch64-linux-ohos 工具链）编译以下代码失败：

```cpp
static __thread std::random_device rd;
static __thread std::uniform_int_distribution<uint64_t> dist(0, (uint64_t)(~0));
```

```
error: type of thread-local variable has non-trivial destruction
error: initializer for thread-local variable must be a constant expression
```

实际案例：`sole`（r-lyeh/sole，header-only C++11 UUID 库）的 `uuid4()` 内建实现。

## 根因

GNU `__thread` 关键字的语义限制：
1. TLS 变量的初始化必须是**常量表达式**（constexpr）；
2. TLS 变量的类型必须具有**平凡析构**（trivial destructor）。

`std::random_device` 具有非平凡析构（内部持有熵源句柄），
`std::uniform_int_distribution<uint64_t>` 的构造函数不是常量表达式，
两者均不满足 `__thread` 的要求，clang 15 直接拒绝。

标准 C++11 `thread_local` 关键字**支持动态初始化与非平凡析构**，
在 clang / gcc / MSVC 上均可移植使用，是正确替代。

## 修复方案

把 `__thread` 改为 `thread_local`：

```cpp
static thread_local std::random_device rd;
static thread_local std::uniform_int_distribution<uint64_t> dist(0, (uint64_t)(~0));
```

对 `$msvc(__declspec(thread)) $melse(...)` 这类多平台宏，仅需替换非 MSVC 分支。

## 验证结果

| 步骤 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| 编译 | `/data/service/hnp/bin/clang++ sole.cxx -std=c++11 -O2` | 0 | 通过 |
| 上游测试 | `./sole-tests-ohos` | 0 | run::verify 1M 序列化往返通过 |
| 消费者 | `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 ...` | 0 | test_sole 编译/链接/运行通过 |

## 适用边界

- **适用**：C++11+ 代码中 `static __thread` 用于具有非平凡析构或非常量初始化的类型（std::random_device、
  std::mutex、std::string、自定义析构类等），clang 报 "non-trivial destruction" / "must be a constant expression"
- **反例**：`static __thread int x;`（平凡 POD 类型）用 `__thread` 合法，无需改动
- **边界差异（与 E026）**：E026 是 glibc 特有 TLS 扩展（tls_model）在 musl 上不支持，推荐标准
  `_Thread_local`/`__thread`；本条目是 `__thread` 自身对类型的要求（平凡析构 + 常量初始化），
  唯一正确选项是 `thread_local`。平台维度（E026）与编译器语言语义维度（本条）互补，不重复。

## 查重结论（七轴）

| 轴 | 结论 | 说明 |
|----|------|------|
| exact_duplicate | false | 图谱/草稿/文档均无 "non-trivial destruction / constant expression" 条目 |
| causal_duplicate | false | 无同根因条目 |
| trigger_overlap | 部分 | 与 E026 均属 TLS 关键词触发（thread_local/__thread），但报错签名不同 |
| solution_overlap | 部分 | E026 推荐标准 `_Thread_local`/`__thread`；本条指出非平凡类型必须用 `thread_local`，互补 |
| combination_novelty | true | "__thread + 非平凡析构类型 + clang 15" 组合未见既有条目 |
| boundary_novelty | true | 新增 "__thread 仅限平凡类型/常量初始化" 边界（E026 未覆盖） |
| test_migration_novelty | false | 不涉及测试迁移 |

关系字段：`similar_to: E026`；`caused_by: -`；`prerequisite_of: -`；`conflicts_with: -`
（与 E026 不冲突，属不同维度互补）

## 路径决定

- 候选已实测验证、可跨库复用、查重为部分覆盖且存在新增差异 → **new_draft**（路径 B）
- 与 sole 1.0.4 归档文件进入同一 PR