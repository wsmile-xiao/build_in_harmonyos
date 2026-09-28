# DRAFT：OpenFst 1.7 → 1.8 消费方 API 迁移（类型 / 全局 flag / 签名三类）

> Status: **Draft**（待审核 promote）| severity: `P1` | category: `build-system` | Updated: 2026-09-26
> 对应: `knowledge/drafts/DRAFT-ohos-openfst-1.8-consumer-api-migration.kv`
> 来源: kaldi g20231112 适配（feat/kaldi-g20231112）

---

**匹配关键词**：fst/types.h, FST_FLAGS, ArcMapFst, MapFstOptions, FstPrinter, StateIteratorData, CompactFst, WriteFst, GetPrecisionString, OpenFst 1.8

## 错误签名（error_signature）

```text
fst/types.h.*file not found|no member named .FST_FLAGS|no matching function for call to .stptri_|no viable overloaded .=.*StateIterator
```

## 错误摘录（error_excerpt）

```text
../base/kaldi-types.h:44:10: fatal error: 'fst/types.h' file not found
fstext/fstext-utils-inl.h:166:3: error: use of undeclared identifier 'Map'
fstext/table-matcher.h:218:11: error: unknown type name 'uint64'
```

## 根因（root_cause）

OpenFst 1.8 是破坏性版本：任何按 1.7 编写的消费方库都会在**多个互不相关的头文件**上分别报
“类型未定义 / 名字不存在 / 无匹配重载”，很容易被误判成多个独立 bug。

| OpenFst 1.7 | OpenFst 1.8.4 |
|---|---|
| `<fst/types.h>` 提供全局 `int8..uint64` | 头文件删除 |
| `FLAGS_xxx` | `FST_FLAGS_xxx` |
| `MapFst` / `MapFstOptions` | `ArcMapFst` / `ArcMapFstOptions` |
| 自由函数 `Map()` | `ArcMap()` |
| `FstPrinter::Print(std::ostream*, ...)` | `Print(std::ostream&, std::string_view)` |
| `FloatWeightTpl::GetPrecisionString()` 返回 `const std::string&` | 返回 `std::string_view` |
| `MatcherBase::Properties(uint64)` | `Properties(uint64_t)` |
| `StateIteratorData::base` 裸指针 | `std::unique_ptr` |
| `CompactFst::WriteFst()` 静态成员 | 已移除，改实例 `Write()` |

## 推荐处置（rec_approach）

按“类型 / 名字 / 签名”三类**一次性整体迁移**，不要按报错点零散修补（会连续多轮踩下一个签名）：

1. 被删的 `<fst/types.h>` → 在消费方自有基础头里用 `<cstdint>` 复刻全局别名
   （`using int8 = int8_t; ... using uint64 = uint64_t;`）；
2. `FLAGS_<fst 全局 flag>` → `FST_FLAGS_*`；注意库自有的 `FLAGS_v` 之类要区分；
3. 类型/函数改名：`MapFstOptions → ArcMapFstOptions`、`MapFst< → ArcMapFst<`、自由函数 `Map( → ArcMap(`
   —— **必须用“前缀不是标识符字符且不是 `.`/`->`”的边界正则**，否则会误改库自身的
   `CreateMapFst()`、`xxx.Map(...)` 成员调用；
4. `printer.Print(&os, "<unknown>")` → `printer.Print(os, "<unknown>")`；
5. `data->base = new X(...)` → `data->base.reset(new X(...))`；
6. `CompactFst::WriteFst(fst, compactor, os, opts)` → `fst::StdCompactAcceptorFst f(fst); f.Write(os, opts);`
   （`CompactFst::Read` 仍然存在，读侧不用改）；
7. 另外 OpenFst 1.8 头文件要求 **C++17**（`std::shared_mutex`/`is_convertible_v`/`optional`），
   消费方若写死 `-std=c++14` 需放到 `-std=c++17` 之后覆盖。

## 影响面（可复用性）

不限于 kaldi：任何 `find_package(kaldi)` / 直接链接 `libfst` 且代码基于 OpenFst 1.7 API 的库
（语音、NLP 的 WFST 工具链）升级到 1.8 时都会命中同一组签名。1.8 起 `MapFst`、`Map()`、
`FLAGS_*`、`fst/types.h`、`CompactFst::WriteFst` 是最高频的 5 处。

## 验证

kaldi g20231112：应用本迁移后 21 个 `kaldi-*.a` 全部编译通过，上游 `make -C src test`
123/123 测试通过（`archives/k/kaldi/g20231112/reports/test-report.md`）。
