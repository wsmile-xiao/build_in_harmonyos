# console-setup 1.248 — HarmonyOS PC 适配说明

console-setup 是 Debian 文本控制台字体与键盘配置工具（console-common 的官方
继任者，后者已 DEPRECATED）：`setupcon(8)`（sh，约 1300 行）按
`/etc/default/keyboard` + `/etc/default/console-setup` 配置加载键图（ckbcomp
→ loadkeys）与字体（setfont），`ckbcomp(1)`（perl）把 xkb 布局编译为
loadkeys 键图。上游 Debian native 3.0 源码
（`console-setup_1.248.tar.xz`），Makefile 纯编排（gzip acm + perl 脚本生成
compose/dkey + bdf2psf 字体转换，**无 C 编译段**），**上游 0 测试用例**
（tar 树核对：无 t/ 目录、无 make check 目标；`Fonts/test_ncurses.pl` 为孤儿
文件——不被任何 Makefile 引用、无运行入口）。

## OHOS 适配点

### 1. 构建期：上游 Makefile 三步真实执行（无 C 编译，全 perl 脚本驱动）

| 上游目标 | 产物 | 耗时（OHOS 实测） |
|---|---|---|
| `make gzipped-acmfiles` | `acm/*.acm.gz`（27 charmap） | <1s |
| `make compose-files dkey-files` | `Keyboard/compose.*.inc` + `dkey.*.inc`（27+27） | ~7s |
| `make -C Fonts gzipped-linux-fonts -j4` | `Fonts/*.psf.gz`（744 字体） | ~3min |

- 字体构建用 `make -C Fonts` 直达子目录 Makefile（`fntdir ?= $(shell pwd)`
  自包含）——顶层 Makefile 的 `.`/`~` 宏重定义为 maindir（`# The following
  two shortcuts will be redefined`），顶层目标名有歧义，子目录目标更稳。
- `make -j4` jobserver 在 OHOS 报 `mkfifo: Operation not permitted` 但不
  阻塞（make 回退语义，进程并行实测正常）。
- 字体转换用包内 `Fonts/bdf2psf`（perl，仅 strict/warnings 核心模块），
  193 个 BDF 源随 tarball 提供，hex2bdf/bdfresize/otf2bdf 外部命令规则
  不触发（目标 BDF 已存在 make 跳过）。

### 2. ekmaps 不预生成（构建期 vs 运行期成本取舍）

- `kbdcompiler`（perl）单模型 >5min（OHOS 上 290s timeout 实测超时，5 个
  模型 >25min 超 CI 预算）——不可用于构建期预生成 `*.ekmap.gz`。
- `ckbcomp` 运行期 0.68s/布局生成等价键图（`-I<ckb>` 参数，**`-I` 后无
  空格**——带空格被拆两参数报 "no ACM"）。
- 上游 `install-ckbcomp` 目标（完整 ckbcomp 路径）不依赖 ekmap；ekmap 仅
  `install-ckbcomp-mini`（ckbcomp-mini 路径）消费。本包装完整 ckbcomp，
  ekmap 由运行期按需生成——记环境边界。

### 3. 包布局 = 上游 /usr 前缀映射（installdir 自解析，零硬编码 patch）

`setupcon` L389-394 与 `ckbcomp` L42-50 用同一逻辑推导安装前缀：
`installdir=${0%/*}` 去尾 `/bin`，`[ -d "$installdir/bin" ]` 回退 /usr。
conan 包按上游 `/usr` 前缀映射到 `$pkg`，`bin/` 下运行时两者都自动解析
到 `$pkg`：

| 上游（Debian） | 归档包 | 消费方 |
|---|---|---|
| `/bin/setupcon`（bootprefix） | `bin/setupcon`（0755，`#!/bin/sh` 保留） | — |
| `/usr/bin/ckbcomp` | `bin/ckbcomp`（0755，env perl shebang） | setupcon 调 `$installdir/bin/ckbcomp` |
| `/usr/share/consolefonts/*.psf.gz`（744） | `share/consolefonts/`（构建产物） | setupcon `findfile share/consolefonts` |
| `/usr/share/consoletrans/*.acm` | `share/consoletrans/`（原始 .acm，27） | ckbcomp `-charmap` 搜索顺序第 3 项直接读（.gz 路径依赖运行时 zcat，原始文件零工具依赖） |
| `/etc/console-setup/ckb/`（完整 ckbcomp 模式，Makefile L52-54） | `etc/console-setup/ckb/` | ckbcomp `@xdirs[0]`/`[1]`（L53-54 `/etc/console-setup/ckb` 与 `$installdir/etc/console-setup/ckb`——包布局 $pkg=/usr 时重合；share 路径不在 @xdirs 中） |
| `/etc/console-setup/compose.*.inc` + `dkey.*.inc` + `remap.inc` | `etc/console-setup/`（构建产物 27+27+1） | ckbcomp `-compose`（L4822-4844 `$installdir/etc/console-setup/` 回退） |
| `/etc/default/keyboard` + `console-setup` | `etc/default/` | setupcon `MAIN_CONFIG`/`MAIN_CONFIG2` 的 installdir 回退路径（L411-418） |
| `man/setupcon.1` `ckbcomp.1` `keyboard.5` `console-setup.5` | `man/man1/` `man/man5/`（上游 tarball 已含预渲染） | 文档 |
| `GPL-2` | `licenses/` | 许可 |

实测验证：完整包布局下 `bin/ckbcomp us` RC=0（142 行，108 行 keycode
映射）；`bin/ckbcomp -charmap ISO-8859-1 us` RC=0（142 行，acm 原始文件
路径命中）——两条数据路径全通。

### 4. shebang 适配（13 个 perl 脚本）

`#!/usr/bin/perl` → `#!/usr/bin/env perl`（OHOS 无 `/usr/bin/perl`，perl
由 hnp 提供 `/data/service/hnp/bin/perl`，house perl shebang 先例）。
**尾随空格陷阱**：上游 shebang 为 `#!/usr/bin/perl␣`（od 复核 16 字节，
perl 后带 1 空格）——精确字符串替换静默不命中，必须正则
`^#!\s*/usr/bin/perl[ \t]*\n` 容忍行尾空白（dryrun 复现：替换不命中 →
make 执行 bdf2psf 报 `No such file or directory` Error 126，实为内核
解析 shebang 解释器失败）。

清单（tarball 首行 `#!/usr/bin/perl` 权威核对）：
`Fonts/bdf2psf`、`Fonts/fbsdmap`、`Fonts/fontcodesets`、
`Fonts/test_ncurses.pl`、`Keyboard/KeyboardNames.pl`、`Keyboard/ckbcomp`、
`Keyboard/compose_translator`、`Keyboard/dkey_bsd`、`Keyboard/kbdcompiler`、
`Keyboard/kbdnames-maker`、`Keyboard/make_charmap_functions`、
`Keyboard/xmlreader`、`describe_unicodes`。
`setupcon`/`Keyboard/ckbcomp-mini` 为 `#!/bin/sh` 保留（OHOS 有 /bin/sh）。

### 5. 依赖（conan requires）

运行期外部命令消费关系（setupcon/ckbcomp 全文核对）：

| 命令 | 归属包 | 已归档 | 声明 |
|---|---|---|---|
| `loadkeys`/`setfont`/`kbd_mode` | kbd | kbd/2.9.0 | `requires` |
| `tempfile` | **setupcon L64 shell 内建函数**（mktemp 回退） | — | 不声明（非 debianutils 外部命令） |
| `gzip`/`zcat` | OHOS 基础系统（/usr/bin/zcat 实测存在） | — | 不声明 |
| `fbset`/`vidcontrol`/`consolechars`/`locale` | 虚拟终端工具（`which` graceful 探测，缺失降级） | — | 不声明（环境边界） |

与 console-common 的差异：install-keymap 调 `dpkg --print-architecture`
+ debianutils `tempfile` 外部命令，而 setupcon/ckbcomp 全文无 dpkg 消费、
tempfile 为内建——依赖归属按脚本全文核对，不凭同生态包类比声明。

## 测试

上游 0 测试 → 自写冒烟 `test_package/test_console_setup.sh`（12 项，断言点
全部来自脚本全文核对 + 完整包布局实测）：

1. `setupcon` 在 env PATH（runenv bindirs 注入）；
2. `setupcon --help` → exit 0 + Usage（参数解析前分支，确定性行为）;
3. `setupcon` 无参 → exit 1 + "None of /etc/default/keyboard"（配置缺失
   早退分支，实测 RC=1）；
4. `setupcon` 未知选项 → exit 1 + "Unrecognised option"（实测 RC=1）；
5. `ckbcomp -help` → exit 0 + "Usage: ckbcomp"（实测 RC=0）；
6. `ckbcomp us` 生成键图（142 行含 108 行 keycode——运行期 perl 解析
   `$pkg/share/console-setup/ckb` 数据，installdir 自解析验证）；
7. `ckbcomp -charmap ISO-8859-1 us` RC=0（acm 原始文件路径命中）；
8. `setupcon --save-only` 生成键图缓存（ckbcomp 落盘路径，需 --setup-dir
   指可写目录）——若触发 VT 探测失败则按降级分支断言；
9. 744 个 `share/consolefonts/*.psf.gz` 落位 + gzip 魔数抽样校验
   （解压前 2 字节 `04 36` PSF1 magic）；
10. `share/consoletrans/` 27 个 .acm + `etc/console-setup/` 55 个 .inc
    （27 compose + 27 dkey + 1 remap）落位；
11. `share/console-setup/ckb/` 数据落位（rules 17 + symbols 135 +
    geometry 27 + keycodes/types/compat）；
12. perl 脚本 shebang 已适配（bin/ckbcomp 首行 `#!/usr/bin/env perl`）
    + `etc/default/keyboard` + `console-setup` 配置落位。

## 边界

- **虚拟终端路径未适配**：setupcon 核心功能（loadkeys/setfont 加载）需
  真实 Linux VT + root（`/dev/console`、`/dev/tty*`），OHOS 无——非 root
  冒烟只走确定性早退分支（--help/无参/未知选项）与 ckbcomp 键图生成
  （纯文本转换，不触达 VT）。
- **ekmaps 不预生成**：kbdcompiler 单模型 >5min 超 CI 预算（290s 超时
  实测），ekmap 由运行期 ckbcomp 按需生成（0.68s/布局）——mini 路径
  （ckbcomp-mini + ekmap 预生成）不适配，本包装完整 ckbcomp 路径。
- **fbset/vidcontrol/consolechars 缺失降级**：setupcon 的 framebuffer
  字体模式（VIDEOMODE/`--font-only` + fb 探测）需这些工具，OHOS 无——
  `which` graceful 探测降级为 VGA 模式路径，不触达。
- **`--setup-dir` 写入路径**：setupcon `--save-only` 向 `$setupdir/etc/
  console-setup/` 写缓存——测试用工作目录模拟，不写 /etc。
- `Fonts/test_ncurses.pl` 为孤儿文件（无 Makefile 引用、需 ncurses
  开发库）——不纳入测试。
