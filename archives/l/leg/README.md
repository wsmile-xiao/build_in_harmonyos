# leg

> Ian Piumarta 的递归下降解析器生成器（peg/leg），从 PEG 或 LEG 文法生成 C 解析器

## 简介

`leg` 是本仓库对 **peg/leg** 项目的包名。上游只有一个源码树和一个发行包
`peg-<version>.tar.gz`，**同一个 tarball 会构建出两个可执行文件**：

- `peg` — 从 Ford 风格的 PEG 文法生成递归下降解析器；
- `leg` — 同一引擎的 lex/yacc 替代风格前端（`%{ %}` 头部 + `%%` 尾部）。

上游没有独立的 `leg-<version>.tar.gz`，`0.1.18` 也是 peg 项目的版本号
（`src/version.h` 中 `PEG_MINOR=1`、`PEG_LEVEL=18`）。用 `leg` 作为包名与
发行版惯例一致：Homebrew 的 `peg` formula 标注 “Also known as: leg”，
Debian/Alpine 的 `peg` 包里 `leg` 是被同时安装的命令。

本包是工具包（`package_type = application`），不产出库与公共头文件。

## OHOS 适配要点

- 上游是裸 Makefile 项目，无 `configure`、无 autotools、无 CMake。配方用
  `basic_layout` + `VirtualBuildEnv`，直接从 `tools.build:compiler_executables`
  取 C 编译器并以 `make CC=<compiler> -j1` 构建。
- **必须 `-j1`**：HarmonyOS 上 make 无法创建 jobserver fifo（Operation not
  permitted），GNU make 只在非并行模式下容忍该失败。
- 上游 `install` target 内硬编码 `strip` 并使用非标准的 `ROOT`/`PREFIX`
  （不是 `DESTDIR`），因此配方不调用 `make install`，而是在 `package()` 中
  直接复制 `bin/peg`、`bin/leg` 与 `src/peg.1`。
- 源码零修改：全部为 C 与 POSIX 标准库调用（`stdio`/`stdlib`/`string`/
  `assert`/`unistd`/`libgen`），无平台特定分支。

## 上游测试

`conanfile.py` 的 `build()` 中真实执行两个上游 target：

| target | 内容 | 用例数 |
|--------|------|--------|
| `make check` | 自举一致性：用刚构建的 peg/leg 重新生成 `src/peg.peg-c`、`src/leg.c`，与发行包内预生成文件逐字节 diff | 2 |
| `make test` | `examples/` 端到端回归：生成 C → 编译 → 喂输入 → 与 `.ref` 参考输出 diff | 11 |

`examples/` 的 11 个用例：`test`、`rule`、`accept`、`dc`、`dcv`、`localpeg`
（走 peg），`wc`、`calc`、`basic`、`localleg`、`erract`（走 leg）。

`test_package/test.sh` 从消费者视角另加 11 条断言：校验两个命令存在且版本号
正确，并分别用 PEG 文法与 LEG 文法生成 C 源码，断言生成物包含 `yyparse`、
语义动作体与 `yytext` 捕获。

## 功能验证

```bash
# 两条命令都来自同一个包
peg -V        # peg version 0.1.18
leg -V        # leg version 0.1.18

# PEG 文法 → C
printf 'start <- "hello" { printf("hi\\n"); }\n' > g.peg
peg -o g.c g.peg

# LEG 文法 → C
printf '%%{\n#include <stdio.h>\n%%}\n\nstart = < [a-z]+ > { printf("%%s\\n", yytext); }\n\n%%%%\n\nint main(void){ while (yyparse()); return 0; }\n' > g.leg
leg -o g2.c g.leg
```

## 已知限制

- 上游只发行 `peg.1` 一份 man page，`leg` 命令与其共用手册页；本包同样只安装
  `man/man1/peg.1`（不伪造 `leg.1`）。

## 参考

- [上游项目页](https://www.piumarta.com/software/peg/)
- [仓库内同类包 archives/p/peg](../../p/peg/README.md) — 同一上游的 0.1.19 版本
