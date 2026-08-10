# ispell 3.4.06 适配笔记

## 概述

ispell 是经典的 Unix 交互式拼写检查器，纯 C 实现，依赖 ncurses 提供终端 UI。
构建系统为传统 Makefile，无 configure 脚本，需要手动配置 `local.h`。

## 关键适配点

### 1. 源码归档

上游站点不再提供 3.4.06 的归档下载。配方使用 Debian 保存的原始
发布包 `ispell_3.4.06.orig.tar.gz`，其 SHA256 已固定在
`conandata.yml`：

```text
17c91633d4c8075acc503163a16463fc54ab1c7453280ad39cd3db75c783eba6
```

### 2. local.h 配置

ispell 需要 `local.h`（从 `local.h.samp` 复制）才能编译。
配方在 `source()` 中自动完成此步骤。

Makefile 支持通过命令行变量覆盖 `local.h` 中的设置，已设置：
- `CC` → 从 Conan toolchain conf 获取的 clang
- `TERMLIB` → `-lncursesw`
- `TERMINCLUDE` → ncurses 包的 include 路径
- `LANGUAGES=""` → 跳过需要 Perl 和 wordlist 数据的语言字典构建

### 3. ncurses 依赖

ispell 使用宽字符 ncurses（`libncursesw`），依赖 `ncurses/6.5`。
需要先确认此依赖已发布到 OHOS Conan 制品仓：

```bash
conan download "ncurses/6.5" -r=ohpcd --only-recipe && echo "OK"
```

若未发布，需先适配 ncurses/6.5。

### 4. LANGUAGES="" 的含义

ispell 上游 Makefile 在 `make install` 时会尝试安装英语词典（需要 Perl + 数据文件）。
通过传递 `LANGUAGES=""` 跳过此步骤，只安装核心二进制工具。
用户自行安装词典（如 `iamerican`、`ibritish` 等包）。

### 5. 鸿蒙真机适配（8 处源码/构建拦点）

配方在 `source()` / `build()` / `package()` 段用 `replace_in_file` / `save` / 命令行变量处理了 8 处鸿蒙真机兼容拦点，均在上游 ispell 配方范畴、本轮真机验证逐个定位：

| # | 拦点 | 根因 | 修法 |
|---|---|---|---|
| 1 | `cc: inaccessible or not found` | 上游 `config.sh:` 规则用 sed 从 `config.X` 抽 `CC`，不读 make 命令行变量，config.sh 里 `CC='cc'`（上游默认），鸿蒙真机 PATH 无 `cc` | `make config.sh` 后用 `replace_in_file` 把 config.sh 里 `CC='cc'` 改成 `CC='clang'` |
| 2 | `undefined symbol: rindex` | 鸿蒙 libc 弃了 BSD `rindex`，POSIX `strrchr` 是替代；8 处用点在 `#ifndef USG` 卫内（USG 鸿蒙未定义） | `replace_in_file` 把 buildhash.c + ispell.c 里 `rindex (` 改成 `strrchr (` |
| 3 | `unable to find library -lncurses` | 上游 `config.X` 默认 `TERMLIB='-lncurses'`，鸿蒙 ncurses 包只装了 `libncursesw.a` | `replace_in_file` 把 config.sh 里 `TERMLIB='-lncurses'` 改成 `'-L{ncurses_lib} -lncursesw'`（塞 `-L` 路径因上游 ispell 链规则漏调 `$LDFLAGS`） |
| 4 | `duplicate symbol: BC` | 上游 `ispell.h` 的 `#ifdef MAIN #define EXTERN /* nothing */`——ispell.c 编译时 MAIN 被定义、EXTERN 展开成空，`EXTERN char *BC;` 成 tentative definition（B 段全局），跟 ncurses `lib_termcap.o` 的同名 terminfo `BC` 冲突 | `replace_in_file` 把 ispell.h 里 `EXTERN char *\tBC;` 改成 `EXTERN char *\tispell_BC;` + term.c 里 3 处引用一起 rename |
| 5 | `undefined symbol: sigsetmask/sigblock` | 鸿蒙 libc 弃了 BSD `sigsetmask`/`sigblock`，4 处用点在 `#ifdef SIGTSTP` 卫内（鸿蒙定义了 SIGTSTP） | `replace_in_file` 把 term.c 里 4 处 `sigsetmask`/`sigblock` 调用注成 `(void) 0;` |
| 6 | munchlist 硬链接 `Operation not permitted` | 上游 `all:` → `all-languages` → munchlist 硬调 `ln`，鸿蒙真机 conan cache 目录不许硬链接 | `build()` 段 `make` 改成显式 target `programs ispell.1 ispell.5`（跳 `all-languages`）；`package()` 段 `make install` 改成 `install-basic install-deformatters install-dictbuild` |
| 7 | `cp ispell.1: No such file` | 上游 `install-basic` 硬调 `cp ispell.1`/`ispell.5`，但这两个 man page 是 `all:` 链里生成的（不在 `programs:` 链） | `build()` 段 `make` 加 `ispell.1 ispell.5` 显式 target |
| 8 | `ispell not executable` → `Operation not permitted` | 上游 `install-basic` 用 shell `cp`（不带 `-p`）装 ispell；鸿蒙 MAC（`hmmac=use_task`）拒执行未签名 ELF | `package()` 段对 `bin/ispell` + `bin/buildhash` 做 ELF 重签名（`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` + 原子替换 + `chmod 0o755`），同仓库 daemon/ent/zig 模式 |

### 6. 词典路径绕（test_package `ispell -a`）

ispell 编译时硬编码 `LIBDIR="/usr/local/lib"` + `DEFHASH="english.hash"`（`config.X:318`），test_ispell.sh 的 `ispell -a` 走该默认路径找词典。上游 `install-languages` → munchlist 链用 `ln -s` 软链接建 `english.hash`，鸿蒙 conan cache 目录软链接也拒。

绕法（配方段、不改 test_package 断言）：
- `package()` 段用 `buildhash` 从上游带的 `languages/english/english.aff` + 合并的 `english.{0,1,2}` 词典源直接生成 `english.hash`，装到包内 `<pkg>/usr/local/lib/`（绕 munchlist 软链接链）。
- `test_package/conanfile.py` 的 `test()` 段调 test_ispell.sh 时用 `env ISPELL_DICTDIR=<pkg>/usr/local/lib` 命令行前缀注环境变量——ispell 读词典目录的环境变量名是 **`ISPELL_DICTDIR`**（`config.X:608 #define LIBRARYVAR "ISPELL_DICTDIR"`），不是直觉的 `LIBDIR`。

## 构建状态

- [x] SHA256 已填写
- [x] W0 依赖检查通过（ncurses/6.5 在制品仓）
- [x] conan create 通过（exit 0、主包构建、test_package All ispell tests PASSED）
- [x] test_package 执行通过（ispell -v + ispell -a 管道断言均 PASS）
- [x] 最终包 bin/ispell 存在 `.codesign` section（llvm-readelf -S 验证）
- [x] 鸿蒙真机复验通过（HarmonyOS HongMeng Kernel 1.12.0 aarch64, clang 15.0.4）
