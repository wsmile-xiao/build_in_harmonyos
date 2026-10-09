# 生成器骨架的"仅非 C++"区块边界划错：C++ 模式输出引用只作为成员存在的名字

> Draft: `DRAFT-REFLEX-20241231-CXX-SKELETON-GUARD-MISPLACEMENT`
> Stem: `reflex-20241231-cxx-skeleton-guard-misplacement` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-REFLEX-20241231-CXX-SKELETON-GUARD-MISPLACEMENT
- **严重度**: 1
- **类别**: upstream-defect|codegen|portability
- **触发工具**: clang|reflex
- **阶段**: compilation

## 错误特征

C 模式一切正常（`reflex -o foo.c foo.l` + 编译链接全绿），**只有 C++ 模式**在编译
生成物时炸开，而且报的名字都"看起来像全局变量"，很容易被误判成用户写错了 `%{ %}`：

```
$ reflex++ -t consumer.l > consumer.cc
$ clang++ -std=c++17 -I "$PKG/include" consumer.cc -L "$PKG/lib" -lrefl -o consumer
consumer.cc:...: error: use of undeclared identifier 'yy_current_buffer'
consumer.cc:...: error: use of undeclared identifier 'yy_c_buf_p'
consumer.cc:...: error: use of undeclared identifier 'yy_init'
consumer.cc:...: error: use of undeclared identifier 'yy_start'
consumer.cc:...: error: use of undeclared identifier 'yyin'
consumer.cc:...: error: use of undeclared identifier 'yyout'
（共 10 处；编译器还会误建议 'yy_nxt'，进一步带偏排查方向）
```

观测（2026-09-29，OHOS aarch64，clang 15；reflex 20241231 未打补丁 vs 打补丁后）：

| 构建 | 生成 C 扫描器 | 生成 C++ 扫描器（`reflex++`） |
|------|--------------|------------------------------|
| 未打补丁 | ✅ 生成 → 编译 → 运行全绿 | ❌ 生成成功，但生成物 **10 处 undeclared identifier** 无法编译 |
| 打补丁 0001 后 | ✅ 不变（输出逐字节一致） | ✅ 生成 → 编译 → 运行全绿 |

## 根因

生成器骨架靠**标记**划分语言相关区块。reflex 的 `src/misc.c: skelout()` 规定：

| 标记 | 含义 |
|------|------|
| `%-` | 开始"**仅非 C++** 输出"区 |
| `%+` | 开始"**仅 C++** 输出"区 |
| `%*` | 恢复无条件输出 |
| `%%` | 终止骨架 |

骨架把两个 **C-only** 辅助函数排在 non-C++ 区块**之外**：

```c
"static int yy_init_globals(void)"   /* ← 在 %-…%* 之外 */
"{ ... yy_current_buffer = NULL; yy_c_buf_p = (char *) 0; yy_init = 1; ... }"

"int yylex_destroy(void)"
"{ ... yy_init_globals(); ... }"     /* ← 仍在区块之外 */
```

- **C 模式**：这些名字是文件作用域全局，赋值合法。
- **C++ 模式**：`yy_current_buffer` / `yy_c_buf_p` / `yy_init` / `yy_start` / `yyin` /
  `yyout` 全部是 `yyFlexLexer` 的**成员**，文件作用域不存在 → 编译失败。

所以这是**生成器自身的输出缺陷**，与用户 `.l` 文件无关；也正因为只影响非默认语言路径，
上游"用 C 模式自举复现自己"的回归测试（`make check`）照旧全绿，缺陷被完整掩盖。

## 影响范围

- reflex 20241231 的 C++ 生成路径（`reflex -+` / `reflex++`），以及同血统的 flex 2.5.4
  系骨架。
- 更一般地：**任何"一套骨架 + 区块标记产生多语言输出"的代码生成器**。这类缺陷的判据是
  "默认路径全绿、非默认路径全红"，只在多模式验收下才暴露。

## 推荐方案

**方法**: `wrap-c-only-helpers-back-into-the-non-cxx-guard`

1. **多模式验收**：把生成器的每种语言/模式都真跑一遍，且必须走到
   **生成 → 编译 → 运行**（本包为 C 与 C++ 两条）。只测默认模式 = 漏测。
2. **先怀疑区块边界**：当 C++ 生成物报大量 undeclared identifier、且涉及"本该是成员或全局"
   的名字时，去看骨架的区块标记与落笔函数（`skelout()` / 类似），而不是先改用户侧
   `%{ %}` 或加 `#define` 掩盖。
3. **用骨架自带标记修复**：把 C-only 辅助函数重新包回 non-C++ 区（本例在
   `yy_init_globals` 起始前插 `%-`、在 `yylex_destroy` 收尾后插 `%*`）。这样
   **C 路径输出逐字节不变**，包自带的自举比对仍然成立。
4. **双向回归**：修完必须回跑 C 与 C++ 两条端到端链路，确认没有"修好 C++ 却弄坏 C"。

## 验证命令

```bash
# 打补丁前：C++ 路径必失败
reflex++ -t consumer.l > consumer.cc
clang++ -std=c++17 -I "$PKG/include" consumer.cc -L "$PKG/lib" -lrefl -o consumer   # ← 10 处报错

# 打补丁后：两条路径都必须通过
reflex    -o consumer.c  consumer.l && clang   -I "$PKG/include" consumer.c  -L "$PKG/lib" -lrefl -o c_consumer
reflex++  -t            consumer.l > consumer.cc && clang++ -std=c++17 -I "$PKG/include" consumer.cc -L "$PKG/lib" -lrefl -o cxx_consumer
printf '42 alpha 7 _b9\n' | ./c_consumer   && printf '42 alpha 7 _b9\n' | ./cxx_consumer
make check      # C 路径的自举比对必须仍然逐字节通过
```

## 取证记录

- 包: reflex 20241231（`archives/r/reflex/20241231`）
- 补丁: `patches/0001-skel.c.patch`（+3 行，`type: bugfix`，`platform_only: false`）
- 逐字证据: `archives/r/reflex/20241231/notes.md`（问题 #3）、
  `reports/test-report.md`（T6/T7 两条端到端）、`reports/w3-local-ci.log`
