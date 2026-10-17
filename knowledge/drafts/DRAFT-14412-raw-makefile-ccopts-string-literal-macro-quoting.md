# DRAFT-14412: 手写 Makefile 项目的 `CCOPTS` 里，字符串字面量宏被三层 shell 吃掉引号

- **来源**：metapixel 1.0.2 适配（2026-10-01）
- **领域**：构建系统 / 转义
- **邻近但不同**：DRAFT-10005（musl `strtol` errno）、DRAFT-10035（autotools bootstrap）
  —— 同为编译期条目，但 error_signature 完全不同，本条未被图谱命中

## 现象

手写 Makefile 项目靠命令行覆盖 `CCOPTS` 注入依赖 include 目录，编译却报：

```
metapixel.c:2114:23: error: expected ')'
                printf("metapixel " METAPIXEL_VERSION "\n"
                                    ^
<command line>:3:27: note: expanded from here
#define METAPIXEL_VERSION 1.0.2
                          ^
```

**最迷惑的地方**：conan 日志里 make 的 `RUN:` 行看起来完全正确：

```
RUN: make CC=... CCOPTS="-I. -Irwimg -O2 -DMETAPIXEL_VERSION=\"1.0.2\" ..." -j1 metapixel
```

`\"1.0.2\"` 明明在。错误只出现在 `.o` 的**编译行**里。

## 根因：引号要穿三层 shell

一个 `-DXXX="value"` 形式的宏，从 Python 到编译器要经过：

| 层 | 谁 |
|---|---|
| L1 | conan `self.run` → `/bin/sh -c <整条 make 命令行>` |
| L2 | make 把 `CCOPTS` 展开进 recipe 文本 |
| L3 | recipe 文本再交给 recipe 自己的 `/bin/sh` |
| → | clang |

失败发生在 **L1**：`CCOPTS="... -DXXX=\"1.0.2\" ..."` 里，sh 解析到外层的 `"`
就认为 `CCOPTS` 的值结束了，内层 `\"` 被解转义成真引号，后面全部逃逸成 make 的
额外参数。值交给 make 时已经不含反斜杠，L3 无从恢复 → clang 收到
`-DMETAPIXEL_VERSION=1.0.2`（裸数字）→ 宏展开不是字符串字面量 →
`printf` 拼接处 `expected ')'`。

## 修复：用 `shlex.quote()`，别手写包裹

`shlex.quote()` 对「含空格但不含单引号」的字符串一律选**单引号**包裹。于是 L1 的
sh 把内容**原样透传**给 make，反斜杠留到 L3 才消失：

```python
import shlex

ccopts = " ".join([
    "-I.", "-Irwimg", "-O2", "-Wall",
    '-DMETAPIXEL_VERSION=\\"1.0.2\\"',   # 反斜杠是字面内容
    include_flags,
])
self.run(shlex.join(["make", f"CC={cc}", f"CCOPTS={ccopts}",
                     f"LDOPTS={ldopts}", "-j1", "metapixel"]),
         cwd=self.source_folder)
```

**自检**：打印 `self.run` 的命令行，`CCOPTS` 的值必须显示为
`'... -DMETAPIXEL_VERSION=\"1.0.2\" ...'`（单引号 + 反斜杠可见）才对。

## 排查口诀

> 日志里 make 的 `RUN:` 行看着对，错误却出在 `.o` 的编译行，且是
> `expected ')'` / 宏展开成裸数字 —— 就是引号在 L1 或 L3 被吃掉了。
> **先数 shell 层数，不要改上游源码。**

## 两段式证据链（本条已实测）

| 步骤 | 结果 |
|------|------|
| 手工拼 `f'CCOPTS=\\"{ccopts}\\"'` | 编译失败，note 显示 `#define METAPIXEL_VERSION 1.0.2`（引号已丢） |
| 改用 `shlex.quote()` | `conan create` rc=0，test_package **16/16 PASS**，`--version` 打印 `metapixel 1.0.2` |

反向验证：换回手工包裹立刻复现，确认对转义敏感、**非偶然通过**。

## 适用范围

- 手写 Makefile 的 C/C++ 项目，靠命令行覆盖 `CCOPTS`/`CFLAGS`/`LDOPTS` 注入依赖
- 任何在 `-D` 宏里带字符串字面量（`-DNAME="value"`）的构建
- conanfile.py 里手写 f-string 拼 make/cmake 命令行的场景

## 关联文件

- `archives/m/metapixel/1.0.2/conanfile.py`（`build()` 用 `shlex.join` 注入 `CCOPTS`/`LDOPTS`）
- `archives/m/metapixel/1.0.2/notes.md`（问题 #3）
