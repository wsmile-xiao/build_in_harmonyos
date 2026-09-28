# DRAFT：makefile 的 CC 变量承载"整条编译命令"——命令行 CC= 是整体替换，必须补齐关键 flags

> 来源：simh/3.8.1（上游 V3.8-1，手写 GNU makefile）· 2026-09-27 本机交叉编译 + 真机 shadow CI 实测

## makefile 里 gcc 的三种形态与 CC= 覆盖语义（判据表）

| 形态 | makefile 写法 | 命令行 CC=clang 的效果 | 既有条目 |
|---|---|---|---|
| (a) CC 只含编译器名 | `CC := g++` | 换名即可，上游 flags 保留 | cohomcalg-0.32 |
| (b) gcc 写死在 recipe 正文 | `gcc -o $@ $^` | **无效**，必须改 recipe | cnrbtree-0.3 |
| (c) CC 含完整命令 | `CC = gcc -std=c99 -U__STRICT_ANSI__ -g $(OS_CCDEFS) -I .`<br>`OS_CCDEFS = -lrt -lm -D_GNU_SOURCE` | **整体替换**，上游 flags 全部消失 | **本条（simh）** |

判据：打开 makefile 看 CC 行——**含空格 + flags 即形态 (c)**。

## 形态 (c) 的危害：失败延迟且分散，难归因

覆盖"成功"了（不再报 gcc: No such file or directory），但你悄然弄丢了上游 flags：

- 丢 `-D_GNU_SOURCE` → musl 下 `strncasecmp`/`usleep` 隐式声明，clang 15 下是
  **error**（-Wimplicit-function-declaration 升级为错），且报错点在具体源文件，像代码 bug；
- `-lm` 留在 CC 串里 → 它落在**源文件之前**，链接顺序失效，报
  `undefined reference to fmod/log/exp/sqrt`，像"没链 libm"，实际是位置问题；
- `-lrt` 去留：本例去除（musl 将 clock_gettime 并入 libc）；但注意 rtklib（E628）
  在 LDLIBS 里保留 `-lrt` 亦可链接，该平台有兜底，**非必改项**。

## 处置（simh 实测配方）

```python
compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
cc = compilers.get("c", "clang") if compilers else "clang"      # R33：不碰裸 ${CC}
cc_cmd = f"{cc} -std=c99 -U__STRICT_ANSI__ -O2 -D_GNU_SOURCE -fcommon -I."
self.run(f'make CC="{cc_cmd}" LDFLAGS="-lm" -j1', cwd=self.source_folder)
```

要点：覆盖串**显式重声明**全部关键 flags；库链接移到 LDFLAGS（该 makefile 的链接
规则是 `${CC} <srcs> -o $@ ${LDFLAGS}`，LDFLAGS 恰在源文件之后）。

`-fcommon` 的取舍：simh 代码（1993-2009）依赖 common symbol 合并，clang ≥15 默认
`-fno-common` 会报 duplicate symbol。**根因与推荐修法见
DRAFT-clang-fno-common-header-globals**（该条 forbid 默认加 -fcommon，推荐
extern+单一定义点）；simh 归档是上游发布物、为 26 个 target 重排头文件不可维护，
故按该条的 fallback_approach 使用 -fcommon 并记录技术债务——不是对根因条目的否定。

## 实测证据

- 本机（DevEco OHOS SDK clang-15 交叉）26/26；真机 shadow CI（2026-09-27）同命令
  26/26，L0-L5 全 pass；
- 对照实验：丢 `-D_GNU_SOURCE` / `-lm` 写入 CC 串，均复现对应失败模式。

## 查重边界

与 cohomcalg / cnrbtree / E628-rtklib 合起来构成"gcc 出现位置三形态判据表"，
本条补的是形态 (c)——覆盖看似成功、实际丢 flags 的第三种失效模式，三个既有条目
均未覆盖。全库检索 `make CC` / `hardcoded compiler` / `compiler override`：
无重复。
