# 1990s C 代码漏 include <math.h> 时 sqrt/fabs 走隐式 int 声明，LP64 上 double 结果被截断

> Draft: `DRAFT-lutefisk-1.0.7-lp64-implicit-int-math`
> Stem: `lutefisk-1.0.7-lp64-implicit-int-math` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-lutefisk-1.0.7-lp64-implicit-int-math
- **严重度**: 1（编译全绿，数值静默错误）
- **类别**: portability | arch | numeric-correctness
- **触发工具**: conan | clang | make
- **阶段**: compilation

## 错误特征

这类缺陷的第一个特征是**编译期只有告警、没有错误**：

```
LutefiskHaggis.c:397:18: warning: call to undeclared library function 'sqrt'
    with type 'double (double)'; ISO C99 and later do not support implicit
    function declarations [-Wimplicit-function-declaration]
LutefiskMain.c:2850:11: warning: call to undeclared library function 'sqrt' ...
LutefiskMain.c:2920:9:  warning: call to undeclared library function 'fabs' ...
```

clang 15 在 C99+ 模式下对隐式声明**只告警并继续编译**（clang 16 才升级为错误），
`conan create` 因此全程 rc=0，产出一个能跑、但数学函数返回值被截断成 int 的二进制。

同一批代码里还有 44 条 `-Wformat`，其中两类在 LP64 上是真实错误而不是风格问题：

| 写法 | LP64(aarch64) 上的实际行为 |
|------|--------------------------|
| `printf("%ld", int_val)` | int 写进 w 寄存器后**零扩展**到 x 寄存器，`%ld` 按无符号打印 → 负数变成 4294967295 |
| `printf("%d", sizeof(x))` | `size_t` 8 字节只读低 4 位 |
| `printf("%d", char_ptr)` | 指针被截断 |

对比 x86-64 SysV：`%ld` 读 int 时从 64 位槽取低 32 位并符号扩展，恰好是对的；换到
AAPCS64 零扩展规则就暴露了。

## 根因

1. `LutefiskHaggis.c` / `LutefiskMain.c` 只 include 了 `stdio/stdlib/string/time/unistd`，
   调用 `sqrt()`/`fabs()` 却没包含 `<math.h>`；C89 的隐式声明规则让编译器默认返回 `int`。
2. 这类 1995-2006 年的科学计算程序普遍用 `%ld` 配 `int` 实参（当年 32 位下 printf
   按 int 取参，等价），迁移到 64 位后语义就变了。

## 影响范围

- 1995-2010 年代手写 C 的科学计算工具（生物信息、质谱、天文、化学），尤其自带
  `Makefile.<os>` 而没有 autotools/CMake 的项目。
- 所有 LP64 目标（aarch64 / OHOS PC、x86-64）。
- 只跑 `conan create`（编译+打包+冒烟）而没有「用上游样本数据跑一次真实流程并与
  上游参考输出比对」的验收链路。

## 推荐方案

**方法**: `add-math-include-and-rebuild-with-upstream-reference-data`

1. **在 `source()` 里补 `#include <math.h>`**，不要放 `build()`：Conan 2 的
   `apply_conandata_patches()` 在 `build()` 里可能把补丁打到导出树副本上，而 make 编的
   是原始文件，补丁零作用但日志照样打印 `Apply patch`。
2. **按实参类型逐条改写转换说明符**，验收标准是 `-Wformat` 告警清零。可行做法：让
   clang 输出告警，按「实参在调用实参列表中的序号」定位到格式串里对应序号的转换说明符，
   只替换长度修饰符+转换字符，保留 `%`/flag/width/precision。
   ⚠️ 不要用「从实参位置往回找最近的 `%`」——格式串里所有说明符都排在实参之前，
   这种做法在多实参 printf 上会改错位置（会来回震荡）。
3. **验收必须用上游自带样本 + 作者发布的参考输出**。lutefisk 1.0.7 随包发布了
   `Qtof_ELVISLIVESK.dta` 和作者 2005 年跑的 `Qtof_ELVISLIVESK.lut`；打补丁后重跑，
   top-10 肽段的排序与 `Pr(c)/PevzScr/Quality/IntScr` 逐字一致，只有 `X-corr` 因本地
   libm 差异在小数第三位差 0.002。这才证明修复没有改坏数值路径。
4. **不要顺手改剩下那 9 条告警**（`'/*' within block comment`、非 void 函数缺 return、
   char 与 -1 比较恒假）：它们是上游行为疑点，改了会动数值结果，留在 notes.md 里记录即可。

## 验证命令

```bash
# 1) 补丁前：确认告警存在
clang -D__LINUX -O2 -fsyntax-only src/*.c 2>&1 | grep -c 'warning:'
#   -> 66
# 2) 补丁后
clang -D__LINUX -O2 -fsyntax-only src/*.c 2>&1 | grep -c 'warning:'
#   -> 9（全是上游遗留疑点，故意不改）
# 3) 真实数据往返（这是唯一能证明数值没坏的验证）
lutefisk -q -m 1229.74 -d Lutefisk.details -p Lutefisk.qtof_params \
         -r Lutefisk.residues -s database.sequence -o out.lut Qtof_ELVISLIVESK.dta
awk '/^ *Sequence/{s=1;next} s&&NF>=6{print $1}' out.lut | sort > got.txt
awk '/^ *Sequence/{s=1;next} s&&NF>=6{print $1}' Qtof_ELVISLIVESK.lut | sort > ref.txt
diff ref.txt got.txt && echo NUMERICS_MATCH_UPSTREAM_REFERENCE
```

## 取证记录

- 包: lutefisk 1.0.7（`archives/l/lutefisk/1.0.7`）
- 环境: OHOS aarch64，clang 15，本地 profile `ohos-aarch64-wsl`
- 逐字证据: `archives/l/lutefisk/1.0.7/notes.md` §5 / §8，
  `patches/0001-math-include.patch`、`patches/0002-format-specifiers.patch`