# E545 — 宏生成的解析器/函数定义在 clang 下报 "function definition is not allowed here"

## 错误特征

clang 编译**在函数体内用宏就地定义解析器/局部函数**的 C 源码（如 CParseC 的
`CPC_STRING(name, lit)`、`CPC_ALT(name, x, y)` 等解析器组合子宏在测试函数体内
展开）时报：

```
error: function definition is not allowed here
```

典型日志（cparsec 2.3.0 实测，OHOS clang 15）：

```
test/basic.h:60:5: error: function definition is not allowed here
    CPC_STRING(p_begin_l_, "BEGIN")
    ^
./cparsec.h:225:55: note: expanded from macro 'CPC_STRING'
#define CPC_STRING(name, lit) CPC_DEFINE_PARSER(name) ___CPC_STRING_BODY(lit)
```

无名解析器变体（`CPC_STRING_("END")`，依赖语句表达式 `({ ... })` + 嵌套函数）
在 clang 下同样报错：

```
test/unnamed.c:16:34: error: function definition is not allowed here
    CpcResult result = CPC_PARSE(CPC_STRING_("END"), cpc_slice_from_cstr("END leftovers"), NULL);
                                 ^
./cparsec.h:228:62: note: expanded from macro 'CPC_STRING_'
```

## 触发条件

- 构建系统：任意（Makefile/CMake/autotools 均可触发）
- 阶段：compilation（测试源码编译）
- 编译器：clang 全版本（含 OHOS SDK clang 15）
- 源码特征：header-only 库用宏在函数体内展开函数定义，或语句表达式内嵌函数定义

## 根因分析

宏展开后形成**函数体内嵌的函数定义**（GNU C nested function，gcc 专有扩展），
clang 从 2.0 起从未实现此特性。这与手写嵌套函数（E544）不同：

| 维度 | E544（手写嵌套函数） | E545（宏生成定义） |
|------|---------------------|--------------------|
| 来源 | 源码手写 `int inner(){...}` | 宏展开（CPC_* 解析器宏） |
| 捕获外层变量 | 常见（引用语义） | 通常无（解析器只依赖 input/A/err） |
| 修复 | 提升 + 捕获变量改显式指针参数 | 提升宏调用到文件作用域即可，无需改参数 |
| 无名变体 | 无 | CPC_STRING_ 等依赖语句表达式，需改命名解析器 |

## 解决方案

### 推荐方案：提升宏生成定义到文件作用域 + 无名解析器改命名解析器

1. 把测试函数体内的 `CPC_STRING(p_begin_l_, "BEGIN")`、`CPC_LABEL(...)` 等
   宏调用**整体提升**到文件作用域（名称保持唯一，宏参数原样），函数体内只
   保留 `CPC_PARSE(...)`/断言逻辑。
2. 依赖语句表达式 + 嵌套函数的无名解析器（`CPC_STRING_`、`CPC_ALT_` 等）
   改写为等价的文件作用域命名解析器：`CPC_STRING(p_named_end, "END")`、
   `CPC_ALT(p_combined_inline, p_named_begin, p_named_end)`。
3. 用 `diff -u --label a/... --label b/...` 生成最小补丁放入 `patches/`，
   在 `conandata.yml` 声明补丁条目（conan 应用时路径必须为 `a/xxx` `b/xxx`
   相对源码根的形式）。
4. 重新编译并运行全部测试二进制确认断言通过。

cparsec 2.3.0 实例（全部成功）：

| 文件 | 提升/改写处 | 结果 |
|------|------------|------|
| test/basic.h | 56 处 CPC_* 定义提升文件作用域 | basic.o 58 组 PUTS 断言通过 |
| test/simd.c | 9 处提升（含 QuotedCtx typedef 一并提升） | simd.o 18 组断言通过 |
| test/unnamed.c | CPC_STRING_/CPC_ALT_ 改命名解析器 | unnamed.o 2 组断言通过 |
| examples/example.c | CPC_STRING_(",") 改 CPC_STRING(p_comma,",") | example.o 输出正常 |

### 禁止做法

- ❌ 试图找 clang 开启嵌套函数的编译开关/flag——**不存在**，这是特性缺失。
- ❌ 用 `-Wno-*` 抑制——无效且掩盖错误。
- ❌ 改库头文件（如 cparsec.h）或伪造解析器——破坏库语义与测试真实性。

## 验证

```bash
clang -std=c99 -O3 -Wextra -Wall -Werror -I. -I test test/basic.c -o build/basic.o && ./build/basic.o   # 58 组 PUTS 断言通过
# 全部 6 个上游测试目标编译运行通过；上游 80/80 独立入口通过
```

## 关联条目

- 相关: [E544](E544.md)（手写嵌套函数；本条目为宏生成定义场景，含无名语句表达式解析器变体）
