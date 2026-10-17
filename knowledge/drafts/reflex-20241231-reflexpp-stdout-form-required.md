# `reflex++ -o` 会静默丢掉 `#include <reFlexLexer.h>`：C++ 生成必须走 `-t` stdout

> Draft: `DRAFT-REFLEX-20241231-REFLEXPP-STDOUT-FORM-REQUIRED`
> Stem: `reflex-20241231-reflexpp-stdout-form-required` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-REFLEX-20241231-REFLEXPP-STDOUT-FORM-REQUIRED
- **严重度**: 2
- **类别**: codegen|usage|upstream-defect
- **触发工具**: reflex|clang
- **阶段**: codegen|compilation

## 错误特征

用 `-o` 形式生成 C++ 扫描器时，产物**缺了第一行 include**，直到编译期才以"找不到类型"暴露：

```bash
$ reflex++ -o consumer.cc consumer.l
$ head -1 consumer.cc
# （空 / 直接是 %{ %} 展开后的内容，没有 #include <reFlexLexer.h>）

$ clang++ -std=c++17 -I "$PKG/include" consumer.cc -L "$PKG/lib" -lrefl -o consumer
consumer.cc:...: error: unknown type name 'FlexLexer'     # 实际上头文件路径没问题，是 include 行丢了
```

对照：同一份 `.l`，stdout 形式完好。

```bash
$ reflex++ -t consumer.l > consumer.cc
$ head -1 consumer.cc
#include <reFlexLexer.h>
```

| 调用形式 | 生成物首行 | 结果 |
|----------|-----------|------|
| `reflex++ -o out.cc in.l` | **无** `#include <reFlexLexer.h>` | ❌ 编译失败（缺类声明） |
| `reflex++ -t in.l > out.cc` | `#include <reFlexLexer.h>` | ✅ 编译链接运行全绿 |

## 根因

上游 `src/main.c` 的 `outn()`（约 957 行）**在打开输出文件之前**就把
`#include <FLEXLEXER_HDR>`（`FLEXLEXER_HDR` 已被 GNU 命名变换重定位为
`reFlexLexer.h`）写到 stdout。

- 走 `-t`（stdout）时：这行与后续生成内容同流，一起被重定向进 `out.cc` ✅
- 走 `-o out.cc` 时：这行在输出文件尚未打开时写向 stdout，**被丢弃** ❌

即：这不是路径问题、不是头文件查找问题，而是**生成器在打开输出文件之前输出序言**
这一实现细节的直接后果。

## 影响范围

- reflex 20241231 的 C++ 生成路径（`reflex++` / `reflex -+`）；flex 2.5.4 血统生成器同源。
- 更一般地：任何"序言/声明行在打开输出文件之前写 stdout"的代码生成器。判据是
  **stdout 版本完好而 `-o` 版本缺前导声明**。

## 推荐方案

**方法**: `drive-cxx-codegen-through-stdout-and-assert-first-line`

1. **C++ 消费一律用 stdout 形式**：`<tool> -t foo.l > foo.cc`，不要用 `-o`。
2. **把首行写成显式断言**：在 `test_package` 里断言生成物首行恰为
   `#include <reFlexLexer.h>`。这一步把"静默丢序言"变成硬失败 —— 否则症状会推迟到编译期
   以 `unknown type name 'FlexLexer'` 出现，排查方向会被带偏到头文件搜索路径上。
3. **文档并列给出正误对照**：在 `notes.md`/README 里同时写明 `-t` 与 `-o` 的行为差异，
   避免后续维护者"顺手改成 `-o`"而重新引入。

## 验证命令

```bash
reflex++ -t consumer.l > consumer.cc
head -1 consumer.cc | grep -q '#include <reFlexLexer.h>' && echo PROLOGUE_OK
clang++ -std=c++17 -I "$PKG/include" consumer.cc -L "$PKG/lib" -lrefl -o consumer && ./consumer
```

## 取证记录

- 包: reflex 20241231（`archives/r/reflex/20241231`）
- 逐字证据: `archives/r/reflex/20241231/notes.md`（问题 #4）、
  `test_package/test_reflex.py` 的 T7（断言首行）、`reports/test-report.md`
