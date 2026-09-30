# gperf 生成查表头 size_t 签名 vs 源码手工前置声明 unsigned int（64 位冲突）

> Draft 编号: DRAFT-gperf-generated-header-size_t-signature
> 触发任务: ohcount 3.1.1 适配（task ohcount-3.1.1-r01-pc4-42-20260928T190630Z）
> 状态: pending-editor-review（路径 B 草稿，随 ohcount/3.1.1 归档同一 PR 提交）

## 问题现象

在 aarch64（OHOS）上编译 ohcount 3.1.1 时：

```
src/parser.c:10:20: error: conflicting types for 'ohcount_hash_parser_from_language'
struct ParserMap * ohcount_hash_parser_from_language (register const char *str, register unsigned int len);
                   ^
parsers.gperf:170:1: note: previous definition is here
ohcount_hash_parser_from_language (register const char *str, register size_t len)
^
1 error generated.
```

第二处同类冲突（链接阶段暴露）：

```
languages.gperf:66:1: error: conflicting types for 'ohcount_hash_language_from_name'
ohcount_hash_language_from_name (register const char *str, register size_t len)
^
src/hash/../languages.h:129:21: note: previous declaration is here
struct LanguageMap *ohcount_hash_language_from_name(register const char *str, register unsigned int len);
```

## 根因

1. gperf（≥3.x）生成的查表函数（`-N` 指定的 lookup 函数）以 `size_t` 作为 key 长度
   参数类型。ohcount 的 `src/hash/*.gperf` 经 `gperf -L ANSI-C -E -D -K key -H ... -N ... -t` 生成
   `parser_hash.h`（`register size_t len`）与 `language_hash.c`（`register size_t len`）。
2. 上游 3.1.1 源码在 `src/parser.c`、`src/languages.h` 手工前置声明同一函数原型时写成
   `register unsigned int len`。32 位下 `size_t` 与 `unsigned int` 同宽，编译器不报错；
   aarch64 下 `size_t = unsigned long`，两者类型冲突，clang 报 `conflicting types`
   并指向生成文件中的 `previous definition`。
3. 上游 4.0.0 已把声明修正为 `size_t`（git 历史对比实证），旧 tag（3.1.1）需要同样补丁。

## 修复

将源码侧手工前置声明的 key 长度参数由 `unsigned int` 改为 `size_t`，与 gperf 生成头一致：

```bash
perl -pi -e 's/register unsigned int len\);/register size_t len);/' src/parser.c src/languages.h
```

对应补丁：
- `patches/0006-src-parser.c.patch`
- `patches/0007-src-languages.h.patch`

要求：
- 确认文件已包含 `<string.h>` 或 `<stddef.h>` 提供 `size_t`（parser.c 已有 `#include <string.h>`）
- POSIX 语义，无 `#ifdef __OHOS__`（R8 合规）
- 若 gperf 输出为 .c（如 `language_hash.c`），前置声明可能在 .h 头（如 `languages.h`）中，同样修正

## 验证

```
conan create archives/o/ohcount/3.1.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
UPSTREAM TEST SUMMARY: total=529 passed=529 failed=0 (bindings skipped: 0/10, swig/ruby headers missing)
OHOS SPECIFIC TESTS: 10/10 PASSED
```

## 适用边界 / 反例

- 适用：任何以 gperf 生成查表头并手工前置声明 lookup 函数原型的纯 C/C 库，在 64 位
  （aarch64/x86_64）目标上编译。
- 同型风险：ragel/bison/flex 等其他生成器输出函数签名与手工声明不一致时，同样在
  64 位暴露（bison 调用点数问题见 DRAFT-bison-pure-parser-yylex-signature，是本条目的
  同族反例：那类问题是调用点参数数量，本条是声明类型宽度）。
- 反例：无 gperf 生成头、或声明与生成头已一致的项目不受影响。

## 查重结论（七轴）

| 轴 | 结论 |
|---|---|
| exact_duplicate | false |
| causal_duplicate | false |
| trigger_overlap | true（DRAFT-E5xx 生成源缺失、DRAFT-bison 生成器签名族） |
| solution_overlap | partial（同为 source-patch 声明修正） |
| combination_novelty | true（gperf size_t vs 手工 unsigned int 前置声明具体模式无既有条目） |
| boundary_novelty | true（64 位推进把 32 位可编译的原型冲突暴露为编译错误） |
| test_migration_novelty | false |

关系字段：`similar_to` E065/E196；`caused_by` DRAFT-E5xx-generated-sources-prebuild-patch
（生成源缺失背景）；`prerequisite_of`/`conflicts_with` 无。

## 判定

路径 B（new_draft）：已验证、可跨库复用、四范围查重未命中（引擎零命中）且存在新增
差异。本草稿与 archives/o/ohcount/3.1.1 归档进入同一 PR，不另建脱离三方库的知识库 PR。
