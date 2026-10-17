# reflex

## 简介

REFLEX（Relocalizable Fast Lexical Scanner）是 Thomas Dickey 维护的 **flex 2.5.4 分支**，
被 ncurses 等项目用于生成扫描器。它保留 flex 2.5.4 的经典接口（`yylex()` / `yywrap()` /
`FlexLexer` 类），同时修掉了 2.5.4 的若干历史问题，并额外支持把生成器自身"重定位"
（relocalizable：`flex` → `reflex`、`libfl.a` → `librefl.a`、`FlexLexer.h` →
`reFlexLexer.h`），因此可与系统自带的 flex/bison 生态并存。

- 同仓另有 `re-flex`（[Genivia RE/flex](https://github.com/Genivia/RE-flex)，现代 C++ 重写，非本包）
  与 `flex`（westes flex 2.6.4，上游主线）；本目录对应 **Dickey 的 REFLEX**。

## 交付内容

| 品种 | 路径 | 说明 |
|------|------|------|
| 可执行 `reflex` | `bin/reflex` | 词法分析器生成器（GNU 命名变换 `flex` → `reflex`） |
| 可执行 `reflex++` | `bin/reflex++` | C++ 模式入口（`reflex -+` 的同义词） |
| 静态库 `librefl.a` | `lib/librefl.a` | C 运行时（`main()` + `yywrap()` + `yy_flex_*` 辅助） |
| 头文件 | `include/reFlexLexer.h` | C++ 扫描器基类 `FlexLexer` 与 `yyFlexLexer` |
| 手册 | `share/man/man1/reflex.1` | 上游 manpage |

## OHOS 适配

- 构建系统 autotools，`package_type=static-library`（R26：终端工具静态链接）。
- `config.guess` 无法识别 HongMeng 内核 → 显式传 `--build/--host=aarch64-linux-ohos`；
  两者 canonical 后相等 ⇒ `cross_compiling=no` ⇒ `@no_cross@` 守卫打开，
  `make check`（自举自检）才会真正运行。
- **补丁 0001（bugfix，非平台专用）**：骨架数组 `skel.c` 把 C-only 的
  `yy_init_globals()` / `yylex_destroy()` 排在 non-C++ 守卫区块之外，使
  `reflex++` 生成的所有 C++ 扫描器引用 yyFlexLexer 成员名而无法编译（10 处
  `use of undeclared identifier`）。补丁用骨架自带的 `%-` … `%*` 标记把两函数包回
  non-C++ 区，C 路径行为不变。
- 发布包内 `skel.c` 与 `flex.skl` **内容不一致而 mtime 相同**，`make` 不会重生成
  `skel.c` —— 真正生效的构建输入是发布版 `skel.c`，故补丁打在 `skel.c` 上，并在
  `build()` 用 `os.utime` 强制其比 `flex.skl` 新，避免 `mkskel.sh` 回写覆盖补丁。
- **补丁 0002（portability，平台专用）**：`config.status` 自建临时目录后**立刻**往里重定向
  写文件，当 `TMPDIR` 落在 HMDFS 用户卷（如 `$HOME/.cache/tmp`）时新目录权限元数据尚未生效，
  第一次写入即 `Permission denied`（本地全绿、CI 间歇失败 —— 同一份代码一次失败一次通过，
  属时序竞态而非必现）。补丁去掉 `umask 077` 依赖并显式
  `chmod 700 "$tmp"`；recipe 侧的 `_pin_tmpdir()` 另外在 `configure` 前把 `TMPDIR`/`TMP`/`TEMP`
  钉到经写探针验证的可写根（优先非 HMDFS 的 `/data/storage/el2/base/cache`）。
- E077：OHOS 上 ELF 需携带 `.codesign` 才能执行 → `build()` 内先签名 `flex`
  （`make check` 要执行它），`package()` 内再签名安装出的 `bin/reflex`、`bin/reflex++`。

## 依赖

- 构建工具（`tool_requires`）：`bison/3.8.2`（提供 `YACC = bison -y`）、
  `diffutils/3.12`（`make check` 的逐字节比对需要 `cmp`）。
- 运行期：无外部依赖（静态库自足）。

## 功能验证

```bash
reflex --version          # reflex 2.5.4 / 20241231
reflex++ --version

# C 端到端
reflex -o consumer.c consumer.l
clang -I$PKG/include consumer.c -L$PKG/lib -lrefl -o consumer && ./consumer

# C++ 端到端（注意：必须用 stdout 形式，-o 会丢掉 reFlexLexer.h 的 include 行）
reflex++ -t consumer.l > consumer.cc
clang++ -std=c++17 -I$PKG/include consumer.cc -L$PKG/lib -lrefl -o consumer && ./consumer
```

`test_package/` 中 7 项检查覆盖上述全部路径，其中 2 项为完整的"生成 → 编译 → 链接 → 运行 →
断言词法流"消费者链路（`NUM:42,ID:alpha,NUM:7,ID:_b9`）。

## 上游自检

`conanfile.build()` 已集成上游 `make check`（自举回归：用刚构建的生成器重新生成
`scan.l` → `scan.c`，与发布包预生成的 `initscan.c` 逐字节比对），并额外扫过
`-Ce -Cm -f -Cfea -CFer -l` 六种表压缩模式。上游 `bigcheck` 目标首项为裸 `-C`，
本版选项解析器会把紧随其后的独立参数当作压缩后缀（`./flex: unknown -C option '/'`），
该目标在上游即失败，故 recipe 只驱动可用的 6 种模式。

## 参考

- 项目主页：https://invisible-island.net/reflex/
- 源码：https://invisible-island.net/archives/reflex/reflex-20241231.tgz
- 上游 changelog：https://invisible-island.net/reflex/CHANGES.html
