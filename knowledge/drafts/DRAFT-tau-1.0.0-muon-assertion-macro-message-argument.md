# Muon（jasmcaus/tau）断言宏契约：CHECK/REQUIRE 必须携带消息参数；CHECK_STRNE/REQUIRE_STRNE 为 3 参

> 草稿 DRAFT — 由 tau 1.0.0（jasmcaus/tau = Muon 微单元测试框架，header-only）HarmonyOS PC 适配产生
> 日期: 2026-09-19 | 执行器: pc4-3 | task_id: tau-1.0.0-r01-pc4-3-20260918T174122Z

## 问题

在 Muon 框架（`github.com/jasmcaus/tau`，README/CMake 项目名为 **Muon**）上编写
test_package 消费者测试或自有测试源码时，按其他测试框架的习惯调用断言宏会编译失败：

```c
CHECK(1);                        // error: expected expression
                                 // Muon.h:686: sizeof(char[]){}) —— __VA_ARGS__ 为空
CHECK_STRNE("abc", "abd");       // error: too few arguments provided to
                                 // function-like macro invocation
                                 // 声明为 3 参 (actual, expected, n)
```

首次出现于本库 conan-verify G2（conan create 编译 test_package/test_ohos.c），
误命中知识图谱 E529（Waf/imp，不相关），真实根因是 Muon 断言宏 API 契约。

## 根因

1. `CHECK(cond, ...)` / `REQUIRE(cond, ...)` 宏展开体含
   `if((sizeof(char[]){__VA_ARGS__}) <= 1)`。省略消息参数时 `__VA_ARGS__` 为空，
   展开为 `sizeof(char[]){})` → C 编译器报 "expected expression"。
   因此 Muon 的 CHECK/REQUIRE **必须**携带消息参数（`CHECK(cond, "描述")`）。
2. `CHECK_STRNE` / `REQUIRE_STRNE` / `CHECK_STRNNE` / `REQUIRE_STRNNE`
   声明为 **3 参宏** `(actual, expected, n)`，n 为 `strncmp` 比较长度。
   按 2 参调用报 "too few arguments provided to function-like macro invocation"。

该契约与 Catch2/doctest（消息参数可选）不同，属 Muon 框架自身 API 设计，非 OHOS 平台问题。

## 方案

按上游自身用法调用：

```c
/* 上游 test.c 惯例 */
CHECK(1 < 2, "1 < 2");                          // CHECK(cond, msg)
REQUIRE_STRNE("foo", "foobar", strlen("foo"));  // STRNE 系 3 参

/* 本库 test_package/test_ohos.c 实证通过 */
CHECK(1 == 1, "1 == 1");
CHECK_STRNEQ("tau", "muon");                     // 2 参（无 n 版本）
CHECK_STRNNE("abc", "abd", 3);                   // 3 参，前 3 字符不同则通过
```

STRNE 语义（`__MUONCMP_STRN__(actual, expected, n, cond, ...)`）：

| 宏 | cond | 失败条件 |
|----|------|---------|
| CHECK_STRNE / REQUIRE_STRNE | `!=` | `strncmp(a, e, n) != 0`（前 n 字符不同则失败） |
| CHECK_STRNNE / REQUIRE_STRNNE | `==` | `strncmp(a, e, n) == 0`（前 n 字符相同则失败） |

## 验证

- 修复前：`conan-verify tau 1.0.0` → G2 FAIL（conan-create.log 记录
  test_ohos.c:12/19/20/30 编译错误）
- 修复后：`conan-verify tau 1.0.0` → G1-G4 全过；conan create 中
  `test_tau`、`test_tau_ohos` 2/2 CTest Passed（100%）
- 上游 InternalTests：124/124 suites 通过（OHOS clang15/musl 编译运行）

## 适用边界

- **适用**: 任何将 Muon（jasmcaus/tau）作为测试框架的下游库（如 CSTL 生态），
  或对 Muon 编写 test_package/消费者测试的适配任务
- **不适用**: Catch2 / doctest / GoogleTest 等消息参数可选或宏签名不同的框架
- **反例**: 不能因 Muon 报错就加 `-Wno-error` 或改写宏（R8：不伪造编译通过），
  应按上游契约修正调用

## 查重差异

- `exact_duplicate=false`：无既有 Muon 断言宏条目（正式知识/图谱/草稿四范围 grep 未命中）
- `causal_duplicate=false`：与 E257（G1 header-only build() 门禁）触发点不同
- `trigger_overlap=false`、`solution_overlap=false`：与 E257/E321/E322 的 header-only
  配方族仅 `similar_to` 关系，无方案重叠
- `combination_novelty=true`、`boundary_novelty=true`（2 参/3 参边界明确）、
  `test_migration_novelty=true`（test_package 消费方编译错误模式）
- 关系字段：`similar_to=E257,E321,E322`（header-only 配方族）；`caused_by`/`conflicts_with` 无

## 决定

`new_draft` —— 路径 B（知识库扩展）成立；草稿随本库 PR 交付。
