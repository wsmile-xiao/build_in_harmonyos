# LP64 平台上用 `(unsigned long)` 实现 32 位语义（位移/掩码）会静默算错

> DRAFT · contributor_id: `frj__` · 2026-10-03 · 来源：uasm 2.57 OHOS aarch64 适配（PR #14452）

## 错误特征（可粘贴的真实日志）

没有编译告警、没有链接错误，**产物字节静默不符**。以 uasm 上游回归
`regress/plain_bin/opshr2.asm` 为例（`row = -1; REPT 8 { row = row SHR 4; mov eax,row }`）：

```text
# 期望（上游 regress/exp/plain_bin/opshr2.BIN 前 5 字节）
b8 ff ff ff 0f        # mov eax, 0x0FFFFFFF   (32 位逻辑右移 -1 >> 4)
# 实际（aarch64/OHOS 上直接构建）
b8 ff ff ff ff        # mov eax, 0xFFFFFFFF   (64 位逻辑右移后取低 32 位)
```

`cmp -l` 从第 5 字节起整段错位（3349 处），只出现在含 **负数参与位移** 的用例。

## 触发条件（平台 / 阶段 / 代码模式）

- 平台：OHOS aarch64（LP64，`sizeof(long)==8`）；任何 LP64 目标同理。
- 阶段：编译期（表达式求值 / 常量折叠），编译**成功且无告警**。
- 代码模式：用 `unsigned long`（或 `long`）承载**固定 32 位语义**的位移/掩码/截断，
  例如 `(unsigned long)x >> n`、`(unsigned long)x & 0xFFFFFFFF`、`sizeof(long)==4` 判断。
- 历史背景：这类代码多在 Windows（LLP64，`long`=32 位）上写成并验证。

## 根因分析（机制 + 实测数字）

`long` 在 Windows **LLP64** 下是 32 位，在 OHOS/Linux **LP64** 下是 **64 位**。
`(unsigned long)v >> n` 因此变成 64 位逻辑右移，取低 32 位后仍是全 1：

| 表达式 | 32 位语义期望 | LP64 实际（OHOS aarch64） |
|---|---|---|
| `sizeof(long)` / `sizeof(int)` | 4 / 4 | **8** / 4 |
| `(unsigned int) -1 >> 4` | `0x0FFFFFFF` | `0x0FFFFFFF` |
| `(unsigned long)-1 >> 4` | `0x0FFFFFFF` | `0x0FFFFFFFFFFFFFFF` |
| 上者 `& 0xFFFFFFFF`（取低 32 位） | `0x0FFFFFFF` | `0xFFFFFFFF` |

真机独立小程序（不含 uasm 代码）实测输出：

```text
sizeof(long)=8 sizeof(int)=4
(unsigned long)-1>>4 = 0xfffffffffffffff
(unsigned int )-1>>4 = 0xfffffff
low32(a)             = 0xffffffff
```

uasm 中的原实现（`expreval.c`，`case T_SHR`）正是用 `(unsigned long)` 表达
“32 位 MASM 语义”，且只在 `opnd1->value == -1 && Ofssize == USE32` 时走该分支；
在 aarch64 上该分支给出 64 位结果，导致 `mov eax, -1 SHR 4` 编码成 `0xFFFFFFFF`。

## 解决方案

**推荐**：用定宽类型。把语义上要求 32 位的地方从 `unsigned long` 改为 `uint_32`/`uint32_t`：

```c
/* 改前 */ opnd1->llvalue = (unsigned long)opnd1->llvalue >> opnd2->value;
/* 改后 */ opnd1->llvalue = (uint_32)opnd1->llvalue        >> opnd2->value;
```

修复后 `opshr2` 与上游期望逐字节一致，且 `plain_bin` 403 用例无非期望差异。

**禁止做法（看起来能过但其实错）**：

1. 只用 `-fno-strict-aliasing` / 改优化级别——与位宽无关，问题依旧（位宽由 ABI 决定）。
2. 把 `long` 换成 `long long`/`int64_t`——把 32 位语义“升级”成 64 位，错得更彻底。
3. 指望 `sizeof(long)==4` 的编译期断言——在 LP64 上恒假，会直接断掉或走错分支。

**验证命令**：

```sh
# 独立复现（无第三方依赖）
printf 'int main(){long v=-1;printf("%%llx %%x\\n",(unsigned long)v>>4,(unsigned)((unsigned long)v>>4));}\n' > p.c
clang -O0 p.c -o p && ./p        # => 0xfffffffffffffff 0xffffffff（应关心 32 位时为 0xfffffff）
```

## 通用性证据

- **独立语料（不依赖 uasm）**：上面的最小 C 程序在真机直接复现位宽差异（输出见上）。
- **上游语料**：`regress/plain_bin/opshr2.asm` 改前不符、改后逐字节通过；`plain_bin` 其余
  403 用例同时全绿，说明该修法未引入回归。
- 属于**跨平台通例**：任何“把 `long` 当 32 位”的历史 C 代码在 LP64（OHOS、Linux、macOS）上
  都会命中；Windows(LLP64) 上是隐性的、不报错，所以最容易被漏掉。

## 查重反证

- `LP64`、`LLP64`、`unsigned long`、`位宽` 在 `knowledge/graph/index.tsv`（540 条）与
  `knowledge/drafts/`（1001 条）经精确关键词检索**均为 0 命中**。
- `E113`（`u_int,u_long,u_char,caddr_t`，BSD 类型/compat 头）：讲的是 OHOS **缺少类型定义**，
  需补 typedef/头文件；本条是**类型已存在但位宽语义不同**，非“类型不存在”。
  反证：`grep -i "unsigned long" knowledge/graph/index.tsv | wc -l` → `0`。
- `DRAFT-E999-ohos-musl-long-double-double-alias`：讲 **浮点 `long double`** 被当作 `double`
  （精度宽度）；本条是**整数 `long` 的 32/64 位**，机制与类型均不同。

## 证据（PR / 分支 / 配方 / 日志）

- 分支 `feat/uasm-2.57`，PR #14452，head `2c48e54`。
- 修复点：`archives/u/uasm/2.57/conanfile.py` `build()` 内 `replace_in_file`（源码 `expreval.c`）。
- 真机 `conan create` rc=0；POSIX 回归运行器 oracle 469/477；`opshr2` 由 fail 转 pass。

## 元信息

- authors：`frj__ <241250055@smail.nju.edu.cn>`
- contributor_id：`frj__`；`draft: true`
