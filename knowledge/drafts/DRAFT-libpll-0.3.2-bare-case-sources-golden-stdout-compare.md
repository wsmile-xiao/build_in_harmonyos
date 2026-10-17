# DRAFT：无构建系统注册的裸测试用例源——逐用例编译 + golden stdout 全文比对

> Contributor: CIW | Status: Draft | Updated: 2026-09-21
> Source: libpll 0.3.2 适配（PR #10487，上游 `test/src/*.c` + `test/out/*.out`）
> 同 stem 知识文件：`DRAFT-libpll-0.3.2-bare-case-sources-golden-stdout-compare.kv`

## 错误特征

rule4 判「上游有用例 **21** 个但一个也没测（0/21）」「少报：实测 N=21 > 声明 N=0」。
而检查上游源码：**确实有用例源**（`test/src/<case>.c`）与**参考输出**（`test/out/<case>.out`），
但 `Makefile*` 里**没有** `TESTS` / `check_PROGRAMS` / `check:` ——**测试框架没接入构建系统**。

## 根因分析

这类老式 C 库把测试写成"**独立用例源 + 参考输出**"，靠人工/外部脚本跑；**没有 `make check`**。
于是：
- 审查按**用例源**清点得 N；
- 配方若只 `make all`，这些用例**永远不会被执行** ⇒ 判少报/0 执行。

> 关键认知：**"没有 `make check`" ≠ "没有用例"**。libpll 的 notes 明确写下这一点。

## 推荐方案

**方法**: per-case-compile-and-compare-stdout-to-upstream-golden

```bash
# ① N_static：枚举用例源，排除公共源（common.c 等）
ls test/src/*.c | grep -v '/common\.c$' | wc -l

# ② 逐用例编译（每个 case 一个可执行；公共源一并编译）
for c in test/src/*.c; do b=$(basename $c .c); [ "$b" = common ] && continue
  cc -Iinclude "$c" test/src/common.c -Lbuild -l<lib> -o /tmp/$b || { echo "COMPILE-FAIL $b"; continue; }
  # ③ 执行并把 stdout 与上游 golden 全文比对（不是子串匹配）
  /tmp/$b > /tmp/$b.got && diff -u test/out/$b.out /tmp/$b.got || echo "FAIL $b"
done
```

把 `N_static`（用例源数）/`N_registered`/`N_executed`/未执行分类写进**四处同源**
（正文两张表 + 验证结果 + notes/manifest）。

## 适用范围与反例

- **适用**：老式 C/C++ 库，`test/src` + `test/out` 布局、**未接入** automake/CMake 的 `check`。
- **判据**：`ls test/src/*.c` 非空，而 `Makefile*` 中 `grep -c 'TESTS\|check_PROGRAMS\|^check:'` = 0。
- **陷阱（重要，见 E543-4CD6）**：上游 **golden 可能陈旧**（参考输出早于源码行为修复）——
  比对不一致时，先判定"**是适配问题还是参照物本身过期**"，需要三方证据，不得直接改 golden。
- **边界**：
  - 不得改上游 `test/out/*.out` 去凑通过（那是篡改参照物）；
  - 比对必须**全文**，不得偷偷降级为"包含关键行即可"；
  - 逐用例编译时漏编公共源 = **编译失败**，要在账本里与"用例失败"分开记；
  - 个别用例依赖平台缺失能力（fork/pty/特权）时跑子集并**逐项**给原因，不得整体记 0。

## 验证证据（libpll 0.3.2 / PR #10487）

- `N_static = 21`（tag 0.3.2 的 `test/src/*.c`，22 个 `.c` 排除公共 `common.c`，与 `test/Makefile` 的 `CFILES` 同口径）；
- 配方 `build()` 内**逐用例编译并执行**、stdout 与 `test/out/<case>.out` **全文比对** ⇒ `N_executed = 21`（21/21）；
- 消费者测试另列：`test_package/test.c`（`test_libpll`，7 断言，`test()` 直接执行二进制并断言退出码）。

## 与既有条目的差异（查重结论）

- **E356**（fixed-target compiler ABI 校验）与 **E248**（Makefile.in mtime/automake 重生成）**均无关**；
- **E543-draft-4CD6**（上游参考输出陈旧）只讲**陷阱面**（golden 过期），**未给"如何执行裸用例源"的方法** ⇒ 本条按 **create** 申报，
  并将 E543-4CD6 列为 `similar_to`（陷阱互相引用）；
- 与姊妹条目区分：`DRAFT-mrboom-…upstream-test-entry-unbuildable`（入口**不可构建**）、
  `DRAFT-libsepol-…cunit-suite-with-sibling-tool`（依赖**测试框架+兄弟工具**）——本条是**无框架、靠 golden 比对**的第三类。
