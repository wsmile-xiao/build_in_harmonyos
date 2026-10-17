# TinyFugue 5.2.2 适配笔记

## 当前状态

- 状态: 已在 OpenDesk HarmonyOS PC (aarch64) 上完成构建和消费者测试
- 设备验证: job `20260930-035349-633d01-4task-r15-tinyfugue`，L0/L1/L2/L4/L5 全部通过
- 构建系统: Autotools
- 编译器目标: OHOS aarch64 clang
- 准备日期: 2026-09-30

## 源码选择

最终采用:

```text
https://github.com/ingwarsw/tinyfugue/archive/refs/tags/5.2.2.tar.gz
SHA256: b7d0d914e6ae86f817bee341da77b74a62e22d601e7763e9bc86b074daa8892c
tag: 5.2.2
commit: d9e519a92a76d23e889a0d2717266fdaa3578531
```

`ingwarsw/tinyfugue` 是 README 明确说明的 TinyFugue "Rebirth" 维护仓库，tag `5.2.2` 精确指向上述 commit。Debian 当前源码包名是 `tf`，版本仍是 `4.0s1` 系列，不是 5.2.2，因此 Debian orig tar 不能作为本任务的 5.2.2 来源。

源码归档顶层目录为 `tinyfugue-5.2.2/`，主要结构:

```text
tinyfugue-5.2.2/
  configure
  configure.ac
  Makefile.in
  src/                  C 源码
  unix/                 Autotools/Makefile 片段
  lib/tf/               运行时 tf 脚本库
  lib/py/               Python 辅助库
  lib/lua/              Lua 辅助库
  htmldoc/              文档
  COPYING               GPL-2.0
```

## configure 证据与选择

执行 `sh ./configure --help` 后确认以下选项真实存在:

```text
--disable-ssl
--enable-python
--disable-termcap
--enable-termcap=LIB
--disable-widechar
--enable-lua
```

本配方使用的参数:

```text
./configure \
  --enable-static \
  --disable-shared \
  --disable-widechar \
  --disable-ssl \
  --disable-python \
  --disable-lua \
  --enable-termcap=ncursesw
```

判断依据:

- `--disable-widechar`: 上游 README 明确说明 widechar 依赖 ICU，当前基础包不引入 ICU。
- `--disable-ssl`: 关闭可选 OpenSSL 网络加密支持，避免额外 OpenSSL 依赖。
- `--disable-python`, `--disable-lua`: configure 默认均不启用，显式关闭以保证构建结果稳定。

上游生成的 `configure` 存在一个 Lua 选项缺陷：`--disable-lua` 被解析后仍无条件执行 `enable_lua=yes`，导致 configure 继续查找 Lua 解释器并在缺失时失败。配方在 `build()` 中把赋值改为 `enable_lua=$enableval`，使 `--disable-lua` 真正生效。
- `--enable-termcap=ncursesw`: termcap 是终端 TUI 的核心能力，不能关闭；使用仓库静态 `ncurses/6.4`。
- 未关闭 history、process、float、256colors、mailcheck、inet6 等核心能力。
- 未使用 `--disable-termcap`，因为那会退化到硬编码 vt100 terminal codes。

## 依赖

| 依赖 | 配方中的处理 | 依据 |
|------|--------------|------|
| PCRE2 | `pcre2/10.45` | `configure.ac` 使用 `pcre2-config` 或 `pcre2-8`，缺失时 configure 失败 |
| zlib | `zlib/1.3.1.1` | `configure.ac` 要求 `inflate`，缺失时 configure 失败 |
| ncurses | `ncurses/6.4`（`shared=False`） | `configure.ac` 通过 `AC_SEARCH_LIBS(tgetent, termcap ncurses curses)` 探测 termcap |

`generate()` 同时运行 `AutotoolsDeps`，把 PCRE2/zlib 的头文件、静态库目录和库名注入 configure，避免误用宿主环境依赖。

`AutotoolsDeps` 将 PCRE2、zlib 和 ncurses 的 include/lib 目录注入 configure；配方保留 `-static`，不硬编码设备路径。

## 补丁说明

### 0001-main-long-options.patch

上游只接受短选项，且 `tf --version` / `tf --help` 会被当成非法参数。配方增加与既有短选项输出一致的长选项，供安装后非交互 smoke test 使用。没有修改 TUI、网络或宏引擎行为。

### 构建时版本号替换

上游 `configure` 用 `git describe` 生成版本号，但 GitHub `archive/refs/tags/...tar.gz` 不含 `.git`，会回退成 `development`。`build()` 使用 `replace_in_file` 将精确的回退表达式替换为 `TFVER="5.2.2"`，避免上下文补丁在镜像或不同生成版本上失效。

同一阶段还会修正生成的 `configure` 中 Lua 开关强制为 yes 的缺陷，保证 `--disable-lua` 与配方声明一致。

### 0002-configure-hmdfs-umask.patch

Autoconf 生成的 configure 使用 `umask 077` 创建临时目录，在 OHOS HMDFS 上会触发权限问题。补丁改为 `umask 022`，不改变 configure 逻辑。

## 官方测试统计

上游 5.2.2 没有自动回归测试:

- `configure --help` 仅列出构建功能开关，没有测试开关。
- `Makefile.in`、`unix/Makefile`、`unix/unix.mak` 没有 `check:` 或 `test:` 目标。
- `.github/workflows/build.yml` 的步骤只有 Configure、Build、Install。
- 源码内的 `/test`、`testcolor.tf` 是交互式客户端功能，不构成可自动执行的上游测试套件。

结论: 上游测试 `0/0`。`build()` 中没有伪造 `make check`。

## 消费者测试

消费者测试使用 5 个显式断言验证安装后的 ELF 和自带脚本库，不启动 TUI：

1. `tf` 能从 `PATH` 找到。
2. `tf --version` 包含 `TinyFugue version 5.2.2`。
3. `tf --help` 包含 `Usage:`。
4. `TFLIBDIR` 下的 `stdlib.tf` 存在且非空。
5. `TFLIBDIR` 下至少有 40 个 `.tf` 脚本（实际打包 46 个）。

交互功能限制: 未测试真实 TTY 布局、键盘输入、颜色渲染或 MUD 网络连接；这些属于后续手工验收项，不作为本次消费者 CI 的门禁。

## 已验证范围与未覆盖范围

已在 OHOS aarch64 真机完成：PCRE2、zlib、ncurses/6.4 的链接与构建，`-static` 与 OHOS musl/libc 的链接，HMDFS 上 configure 与安装目录的权限处理，以及安装后二进制和脚本库的消费者检查。

未覆盖：真实终端下的 TUI 渲染/键盘交互和 MUD 网络连接。

<!-- verification: OpenDesk r15 headless consumer test -->
