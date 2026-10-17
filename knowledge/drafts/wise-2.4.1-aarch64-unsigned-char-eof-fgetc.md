# wise 2.4.1：AArch64 `char` 默认无符号使 `fgetc()` + `EOF` 判定失效

> Draft: DRAFT-WISE-241-AARCH64-UNSIGNED-CHAR-EOF-FGETC
> Stem: `wise-2.4.1-aarch64-unsigned-char-eof-fgetc` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-WISE-241-AARCH64-UNSIGNED-CHAR-EOF-FGETC
- **严重度**: 2
- **类别**: platform|portability|aarch64|char-signedness|legacy-c
- **触发工具**: conan|clang|make|perl
- **阶段**: runtime|testing

## 错误特征

编译、链接全部成功，**功能测试**才暴露问题：上游测试套件 12 个用例只通过 4 个，
且失败方式呈现**系统性坐标偏移**而非随机崩溃：

```
Error in promoterwise: <  Length = 798 Reversed 1
Error in promoterwise: >  Length = 797 Reversed 1        # 参考值（pw.mouse 真实长度 797）
Error in basic-cdna:   < 3.75 [31:32 "MATCH_STATE" 1301],[98:101 "CODON" 1301]
Error in basic-cdna:   > 3.75 [31:32 "MATCH_STATE" 1301],[97:100 "CODON" 1301]
Signal 11 (core dumped)
```

关键线索：**蛋白坐标 `i` 正确，只有 DNA 坐标 `j` 与序列长度整体 +1**。
另外 clang 会对源码给出免费信号：

```
warning: result of comparison of constant -1 with expression of type 'char' is always false
         [-Wtautological-constant-out-of-range-compare]
```

## 根因分析

`dynlibsrc/sequence.dy` / `.c` 的 FASTA 读取器（以及 PIR/GCG/EMBL/Zuker 等读取器）：

```c
char c;                        /* ← AArch64 上 char 默认无符号 */
...
c = fgetc(ifp);
if( c == EOF || c == '>' || c == '/' ) break;
seqbuffer[i++] = c;            /* EOF 时写入 (char)(-1) == 0xFF */
```

- AArch64（AAPCS64）与 RISC-V 等目标上，裸 `char` 默认是 **unsigned char**；
  x86_64 上默认是 **signed char**。上游作者与 x86 上的使用者因此从未观察到该问题。
- `c == EOF` 中 `c` 整型提升为 0..255，`EOF` 为 -1，比较**恒假**（clang 会提示
  tautological comparison）。
- 于是读到文件末尾时不 break，而是把 `0xFF` 当作一个碱基写入 `seqbuffer`；
  下一次 `fgetc()` 才真正返回 EOF 退出循环。

由此产生三个可观察后果：

1. **长度 +1**：`make_len_type_Sequence()` 里 `seq->len = strlen(seq->seq)`，序列多一个字节
   → `Length = 798`（真实 797）；
2. **坐标整体偏移**：下游所有 DNA/CODON 坐标由该序列派生 → `[98:101]` vs 参考 `[97:100]`；
3. **段错误**：多出的 0xFF 会进入非 A/T/G/C/N 的转换与索引路径，部分组合下越界
   （estwise / estwisedb / basic-cdna 直接 `Signal 11`）。

`grep` 统计（wise 2.4.1）：12 个源文件声明了 `char c/ch/cc/chr;`，11 处 `!=/== EOF`
比较，集中在 `dynlibsrc/sequence.c`（FASTA/EMBL 等 6 处）、`HMMer2/sqio.c`、
`dnaindex/*`、`base/wisestring.c` 等。

## 复现与定位

```c
/* 一行复现平台差异 */
#include <stdio.h>
int main(){ char c = (char)200; printf("signed=%d EOFeq=%d\n", (c<0), (c==EOF)); return 0; }
```

| 编译方式 | 输出 |
|----------|------|
| `clang -o cs cs.c`（OHOS/aarch64 默认） | `signed=0 EOFeq=0` → 无符号，EOF 比较恒假 |
| `clang -fsigned-char -o cs cs.c` | `signed=1`（`EOFeq` 仍为 0，因 200 不等于 -1，但真实 EOF 可被正确识别）|

上游测试对照（同一份源码，唯一变量是该标志）：

| 编译标志 | 上游 `short.test` |
|----------|-------------------|
| 默认（无 `-fsigned-char`） | 4/12 通过 |
| `-fsigned-char` | **12/12 通过** |

## 解决方案

在构建标志中加入 `-fsigned-char`（wise 2.4.1 配方实测有效）：

```python
cflags = ("-c -O2 -DUNIX -pthread "
          "-fcommon -fsigned-char -Wno-error=int-conversion " + glib_cflags)
```

**为何用全局标志而非逐处 `char` → `int`**：

1. 该模式散布面广（本次 12 文件 / 11 处比较），逐处修改容易遗漏；
2. wise2 的 `.c` 由 dynamite 编译器从 `.dy` 预生成，改 `.c` 会产生 `.c`/`.dy` 分叉；
3. 全局标志同时覆盖**上游测试未触及**的代码路径（如 dnaindex 各读取器）；
4. 该代码处理的是 ASCII 文本数据（序列、矩阵、命令行），恢复其 x86 原始语义
   不会改变正确行为。

**何时不要用全局标志**：若项目的字节处理确实依赖无符号 `char`（哈希、位运算、
二进制协议解析），应改为逐处 `int c;` 或显式 `(unsigned char)` 转换，
避免全局语义切换引入新问题。

## 适用边界

- 适用于把 `fgetc()`/`getc()` 结果存入裸 `char` 再与 `EOF` 比较的遗留 C/C++ 代码；
- 在 x86_64 上不会复现（`char` 默认有符号），因此**不能用"x86 上测试通过"反证**；
- AArch64 / RISC-V / ARM(32) 等默认 unsigned char 的目标都会命中；
- 若代码已使用 `int c;` 或显式 `unsigned char` + `0xFF` 判定，则不受影响。

## 关联

- 本条目来自 wise 2.4.1（EBI Wise2）HarmonyOS PC aarch64 适配；
- 同一适配还涉及：`glib-config`（glib 1.2 时代工具）缺失、HMMer2 局部 `getline()`
  与 POSIX 同名冲突、BSD 专有 `isnumber()`、clang 15 默认 `-fno-common`
  导致 old-style tentative definition 报 multiple definition。
- Debian 在 `wise` 的 arm64 构建中同样关闭了上游测试套件（`override_dh_auto_test`
  仅打印说明后 `# make -C src test`），与其补丁 10（硬编码 `/usr/share/wise/` 数据路径）
  有关；本条目的 `-fsigned-char` 修复与该问题正交。
