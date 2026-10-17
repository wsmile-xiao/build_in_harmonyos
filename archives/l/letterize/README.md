# letterize

`letterize` 是 Eric S. Raymond 的电话号码助记词生成器（BSD-2-Clause），把电话号码
数字展开成**所有可发音的字母助记词**，按美式电话键盘映射：

```
2→ABC  3→DEF  4→GHI  5→JKL  6→MNO  7→PRS  8→TUV  9→XYZ
```

不属于该集合的字符（`0`、`1`、破折号、括号、字母本身）**原样透传**。

程序内嵌一张"可发音字母三元组"词表，只有**所有三元组都在词表中**的候选才会被输出
（约 30% 的三元组被判定为可发音）。因此一个 7 位号码的 19,683 种组合通常会被筛到
几十到几百条，足以人工筛选。

## Versions

| Version | Status | Assertions |
| --- | --- | --- |
| 1.6 | built | 34 |

Homepage: https://gitlab.com/esr/letterize

## 使用方法

```bash
# 展开 234（13 条）
letterize 234

# 展开 7 位号码（78 条）
letterize 5551234

# 展开 10 位号码（246 条）
letterize 5551234567

# 带标点：非数字键原样透传
letterize 1-800-555        # → 1-t00-jjj, 1-t00-jkl, ...

# 只看前几条
letterize 5551234 | head
```

## 输出规模（OHOS aarch64 实测）

| 输入 | 非空行数 | 首行 |
| --- | --- | --- |
| `234` | 13 | `adg` |
| `2275` | 19 | `aarj` |
| `5551234` | 78 | `jjj1adg` |
| `5551234567` | 246 | `jjj1adgkop` |
| `12` | 3 | `1a` |
| `0000000` | 1 | `0000000` |
| `1-800-555` | 18 | `1-t00-jjj` |
| `1` | 1 | `1` |
| （无参数） | 0 | — |

## OHOS 适配

| 项目 | 说明 |
| --- | --- |
| 目标 | `aarch64-linux-ohos`（musl）|
| 源码 | 单 `.c`（`letterize.c` ~13 KB）|
| 外部库 | 无（仅 `ctype` / `stdio` / `stdlib` / `string`）|
| patch | 无 |
| 构建 | 直驱 clang：`clang -O2 -std=gnu99 -o letterize letterize.c` |
| 产物 | `bin/letterize`（约 20 KB）|

### 为什么不用上游 Makefile

上游 `Makefile` 有两处在交叉编译环境里会阻断构建：

1. `CFLAGS += -O -Wall -Werror -Wextra -Wno-parentheses` —— `-Werror` 会把任意告警
   升级为错误；
2. `all: letterize letterize.1`，而 `letterize.1` 由 `asciidoctor -b manpage` 从
   `letterize.adoc` 生成 —— 需要 asciidoctor 工具链。

因此 `build()` 直驱 `clang` 只编译二进制，man 页源文件 `letterize.adoc` 随包安装到
`share/doc/letterize/`。

### char 符号性

aarch64 Linux 默认 `char` 是 **unsigned**（x86-64 是 signed），而本程序的字母三元组
词表按字符值索引。实测 aarch64 与 x86-64 输出行数完全一致
（`234`→13 / `5551234`→78 / `5551234567`→246），说明该实现对 `char` 符号性不敏感，
**无需 patch**。

## 测试

上游**不含任何测试套件**：`Makefile` 的目标是 `all` / `clean` / `spellcheck` /
`reflow` / `install` / `uninstall` / `version` / `dist` / `release` / `refresh`，
**没有 `check` 或 `test` 目标**，源码 tarball 内也无测试源文件或期望输出。

`test_package/test_letterize.c` 提供 **34 条断言**，核心是两条**不依赖硬编码词表**的
结构不变量，对全部输出行逐行逐位校验：

- **P1 长度守恒**：每行助记词长度 == 输入长度（逐位 1:1 映射）
- **P2 键位约束**：第 i 位字符要么 == 输入字符（非 2–9 位原样透传），要么 ∈ 该键位
  字母集合（`2→abc` … `9→xyz`）

配合 8 组实测基线（非空行数 + 首行，用于锚定词表过滤行为与大小写约定）与空输入用例。
属性判据共校验 **353 行**输出的每一位，且**不含任何完整词表副本**——避免把错误输出
抄成期望值而自我固化 bug。

判据全程用 `popen` 内存管道直读子进程输出，**不写任何临时文件**（OHOS 上 `/tmp`
只读）。
