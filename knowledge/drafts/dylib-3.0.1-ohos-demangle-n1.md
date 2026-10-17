# DRAFT-dylib-ohos-demangle-n1：OHOS libc++ std::__n1:: demangle 归一化缺口

> Contributor: AtomCode | Status: Draft | Updated: 2026-09-03
> Source: dylib 3.0.1 第一轮适配（task dylib-3.0.1-r01-pc4-2-20260902T192109Z）

## 问题

上游 gtest 在 OHOS PC 上两个用例失败：

```text
[  FAILED  ] cpp_symbols.functions
C++ exception: Symbol not found: list_add_string(std::vector<std::basic_string<...>> &,
  std::basic_string<char, std::char_traits<char>, std::allocator<char>>)
[  FAILED  ] cpp_symbols.functions_overload_namespace
C++ exception: Symbol not found: tools::adder(std::basic_string<...>, std::basic_string<...>)
```

直接 dlsym(handle, demangled 名) 在 OHOS 上恒失败；dylib 的 fallback 用 demangle 后的
签名做前缀匹配，也失配。

## 根因

- OHOS libc++（libc++_shared.so）把标准库放在内联命名空间 `std::__n1`
  （OpenHarmony ITS / OHOS 分支命名），`abi::__cxa_demangle` 输出
  `std::__n1::basic_string<char, std::__n1::char_traits<char>, std::__n1::allocator<char>>`
- 上游 `format_symbol` 已归一化 Apple libc++ 的 `std::__1::` 与 libstdc++ 的
  `std::__cxx11::`，但**没有覆盖 OHOS 的 `std::__n1::`**，导致基于 demangle 签名的
  模糊符号查找在 OHOS 上失配
- 探针验证：dlsym(mangled) 全部成功，dlsym(demangled) 全部失败——问题确在
  demangle 签名命名空间，而非符号表缺失

## 方案

`format_symbol`（src/format.cpp）增加一行归一化，与既有 __1/__cxx11 处理同族：

```cpp
replace_occurrences(symbol, "std::__n1::", "std::");
```

## 验证

- 补丁后上游 gtest：C++11 16/16、C++17 17/17 全部通过
  （R02 实测 2026-09-07，日志 `/storage/Users/currentUser/tmp/builds/dylib-3.0.1.work/evidence_r02/upstream_tests_r02_full.log`，
  SHA-256 c0d86e248b686162484e168fe355f4c971b97811067c4379215056b2408c05b0）
- HarmonyOS 专项测试（R02 实测 2026-09-07，日志
  `/storage/Users/currentUser/tmp/builds/dylib-3.0.1.work/evidence_r02/ohos_test_r02.log`，
  SHA-256 d697250dcf8c1b94e533d8e421105d578c9faa41959877477fd501438af88058）：
  检查 3962 个 demangled 符号，无 `std::__n1::` 残留
- 符号解析与符号表遍历路径均正常（mangled 名 dlsym 成功）

## 适用边界

- OHOS 上所有依赖 __cxa_demangle 输出做字符串匹配/解析的 C++ 库
- 与上游既有 std::__1::/std::__cxx11:: 归一化同族，属 OHOS 特有缺口
- 注意：__n1 也可能出现在其它 OHOS 分支命名（如 std::__n2）——需要时按同样方式扩展

## 查重差异

- index.tsv：E247 命中 `std::__n1` 关键词，但问题域是 pkg-config --static 静态链接
  传播 libc++ 运行库（Libs.private），**不是 demangle 归一化** → 部分覆盖
- 图谱 E*.kv：无 demangle/__n1 归一化条目 → 未命中
- doc/：E247/E286 均不覆盖本问题域 → 部分覆盖/未命中
- drafts/：无同名草稿 → 未命中
- 查重结论：部分覆盖（E247 提及 __n1 但问题域不同），有新增差异 → 路径 B 候选

## 七轴查重（R02 实测，2026-09-07）

| 轴 | 结论 |
|---|---|
| exact_duplicate | false |
| causal_duplicate | false（E247 根因是 pkg-config 静态链接传播，非 demangle 签名） |
| trigger_overlap | partial（「Symbol not found」触发串与 E286 交叠，但 E286 是 LLVM 插件侧） |
| solution_overlap | true（与上游既有 __1/__cxx11 归一化同族，OHOS __n1 为新缺口） |
| combination_novelty | true（__n1 归一化无既有条目） |
| boundary_novelty | true（显式记录 __n1 仅适用 OHOS ITS 分支，_n2 可能需扩展） |
| test_migration_novelty | true（上游 gtest 在 OHOS 上的失败用例即迁移验证） |

## 关系字段

- `similar_to`: E247（均 __n1，问题域不同）、上游 format.cpp 既有 __1/__cxx11 归一化
- `caused_by`: E247 提及的 OHOS libc++ ITS 命名空间（同根因不同症状）
- `prerequisite_of`: （无）
- `conflicts_with`: （无）

## 覆盖与新增差异（reuse / new_draft 决定）

- 已覆盖部分：E247 覆盖「OHOS libc++ ITS 命名空间 __n1 存在」这一根因事实与静态链接
  传播问题；上游 format.cpp 已覆盖 __1/__cxx11 归一化——均未覆盖 OHOS 下 demangle
  签名的 __n1 归一化缺口
- 本轮新增部分：format_symbol 增加 `std::__n1::` → `std::` 归一化（与既有处理同族），
  并以上游 gtest 失败用例 + OHOS 专项 3962 符号无残留实测验证
- reuse_existing: false（两次四范围查重 + 七轴均无完整重复条目可复用）
- new_draft: true（本 .md/.kv 同 stem 配对，仅位于 knowledge/drafts/）
- path_a_no_knowledge: false（本轮修复含真实可复用知识，非普通配方调整）

## 适用边界

- OHOS 上所有依赖 __cxa_demangle 输出做字符串匹配/解析的 C++ 库
- 与上游既有 std::__1::/std::__cxx11:: 归一化同族，属 OHOS 特有缺口
- 注意：__n1 也可能出现在其它 OHOS 分支命名（如 std::__n2）——需要时按同样方式扩展
- 反例：libstdc++（__cxx11）平台不命中 __n1 文案；不做 demangle 字符串匹配的库不适用

## 验证与恢复条件

- 验证命令（R02 实测）：补丁后上游 gtest C++11 16/16、C++17 17/17 全部通过
  （日志/哈希见上）；OHOS 专项检查 3962 个 demangled 符号无 std::__n1:: 残留
- 恢复条件：若 OHOS 分支命名变化（如 __n2）导致再次失配，按同样方式追加归一化
  并复跑上述验证；若上游自行覆盖 __n1，可移除本补丁
