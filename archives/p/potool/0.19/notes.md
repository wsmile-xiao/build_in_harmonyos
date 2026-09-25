# potool 0.19 适配笔记

## 编译环境
- 构建系统: makefile（**纯 C 裸 Makefile**，无 configure/CMake；G0 探测链与 init-build 模板按 `manifest.build.system=makefile` 显式覆盖）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4（设备 `/data/service/hnp/bin/clang`；**设备 PATH 无 `cc` 别名**，裸 `make` 报 `cc: No such file or directory`，配方必须显式 `CC=clang`）
- 状态: built

## 源与同源核验（W0 关①）

| 项 | 值 |
|---|---|
| 上游 tag | `potool-0.19` = `24703a3eaba4a2ff416b16cd099c33bc7cc098b8`（`git ls-remote --tags https://github.com/porridge/potool`，另有 `upstream/0.19` 同值） |
| 源 A 官方站点 | `https://marcin.owsiany.pl/potool/potool-0.19.tar.gz`（http=200, 19380 B） |
| 源 B Debian pool | `http://deb.debian.org/debian/pool/main/p/potool/potool_0.19.orig.tar.gz`（http=200, 19380 B） |
| sha256（A=B=https 三面全等） | `1251621b5e69b660987e8c9497df9e75e0b3e40bcf8304bdbd26a4fbd37c4384` |
| 源内内证 | `Makefile:9 VER = 0.19`；`git clone --branch potool-0.19` 后 `diff -r --exclude=.git <clone> <tarball>` = 无差异 |
| 上游定位依据 | Debian `debian/control`：`Vcs-Git: https://github.com/porridge/potool`、`Homepage: http://marcin.owsiany.pl/potool-page`；`debian/watch` 指向同一 tarball 模式 |

## 编译步骤

```sh
# 依赖环境（双 profile 与 CI 同构：-pr:h/-pr:b 同用 ci/conan/profiles/ohos-aarch64）
conan install --requires=glib/2.88.3 \
  --tool-requires=flex/2.6.4 --tool-requires=bison/3.8.2 \
  --tool-requires=gettext/0.22.5 --tool-requires=pkgconf/3.0.6 \
  -pr:h=<abs>/ci/conan/profiles/ohos-aarch64 -pr:b=<abs>/ci/conan/profiles/ohos-aarch64 \
  --build=missing -g PkgConfigDeps -g VirtualBuildEnv -g VirtualRunEnv -of <gen>
. <gen>/conanbuild.sh && . <gen>/conanrun.sh
export PKG_CONFIG_PATH=<gen>

make CC=clang CFLAGS="-O3 -pipe -DNDEBUG -g -Wall" -j1   # R9: -j1；R33: CC/CFLAGS 走调用行
make install DESTDIR=<prefix> INSTALL=/system/bin/install  # 设备 PATH 无 /system/bin，install 需绝对路径
make check                                                   # 上游测试，见下
```

- Makefile 用 `$(shell pkg-config --libs/--cflags glib-2.0)` 取 glib，因此 `PKG_CONFIG_PATH` 必须指向 conan 生成的 `.pc` 目录（PkgConfigDeps）。
- `make check` = `cd tests && bash test`（`bash` 由 PATH 解析到 `/data/service/hnp/bin/bash`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | **`-Werror`（任务卡明示的唯一预期改动点）** | 上游 `Makefile:18` 为 `CFLAGS += -g -Wall -Werror`：`-Werror` 把**依赖头与工具链演进**产生的告警升级为硬失败，而目标平台的 glib 头由 conan 提供、CI 与设备工具链不必同版；此为任务卡授权移除的唯一预期改动。**本机实测（如实登记）**：两组控制实验均 rc=0、`grep -ci "warning:"` = 0 —— ①默认 `-g -Wall -Werror`；②配方钉法 `CFLAGS="-O3 -pipe -DNDEBUG -g -Wall -Werror"`（`$TASK_DIR/step2/control-werror.log`）。即本机**不触发**，移除属授权的可移植性预防，不改变诊断面（保留 `-Wall`）。 | `0001-Makefile.patch`：移除 `-Werror`、保留 `-g -Wall`；配方调用行另显式钉 `CFLAGS="-O3 -pipe -DNDEBUG -g -Wall"` |
| 2 | `make check` 报 `scripts/poedit: /bin/bash: bad interpreter ... Error 126` | 设备与 CI worker **无 `/bin/bash`**（`ls /bin/bash` → No such file）；上游 4 个脚本 shebang 硬编码绝对解释器 | `0003/0004/0005` + `0002` 补丁：`#!/bin/bash` → `#!/usr/bin/env bash`、`#!/usr/bin/perl` → `#!/usr/bin/env perl`（`/usr/bin/env` 存在，经 PATH 解析到 `/data/service/hnp/bin/{bash,perl}`）。`tests/test` 的 `#!/bin/bash` **未改**：Makefile 以 `bash test` 调起、不经 shebang |
| 3 | poedit 内 `potool "<file>" -fnth` 报 `Can't open input file: -fnth` | **OHOS = musl libc，`getopt()` 严格 POSIX 不做 GNU 参数置换**。一手探针 `gpprobe`（与 `potool.c` 同 optstring `"f:n:scph"`、同 clang 编译）：`./gpprobe tests/x.po -fnth` → `optind=1 argc=3`、`positional[2]=-fnth`（选项被当位置参数）；`./gpprobe -fnth tests/x.po` → `opt=f optarg=nth optind=2` 正常。`readelf`：`NEEDED libc.so`、`/lib/ld-musl-aarch64.so.1`。上游 `potool.c:652` 用 `getopt()`、`:748` 取 `argv[optind+1]` 当第二输入文件 | `0003-scripts-poedit.patch`：4 处调用改**选项前置**（`$potool -fnth "$POFILE"` 等），同一行错误提示串同步改写；**`potool.c` 解析器不动**（改脚本面最小） |
| 4 | poedit 报 `locale: command not found` → `Failed to retrieve the locale charmap.` | OHOS **全机无 `locale` 命令**（`/system/bin`、`/data/app/bin`、`/data/service/hnp/bin`、`/vendor/bin`、`~/.harmonybrew/bin` 五路全 MISS），`locale` 属 glibc libc-bin 侧工具 | **不改源码**：`build()` 内生成环境 shim `<build>/ohos-bin/locale` 并前置到 PATH，只复刻上游唯一用法 `locale charmap` → `UTF-8`。⚠️ 必须返回 **`UTF-8`**：先返回 locale 名 `C.UTF-8` 实测被 `iconv` 判 `conversion to C.UTF-8 unsupported`（须与 glibc `locale charmap` 对 UTF-8 locale 的真实输出一致才通） |
| 5 | `make install` 报 `make: install: No such file or directory` | 设备 PATH 不含 `/system/bin`（`/system/bin/install` 存在但不在 PATH）；CI worker PATH 含 `/system/bin`，设备侧不显式传则本地必失败 | `make install INSTALL=/system/bin/install`（toybox 0.8.12 实测 `-d`/`-s` 均可用），或按 `command -v install` 回退绝对路径 |
| 6 | 裸 `make` 报 `cc: No such file or directory` | 设备/CI 无 `cc` 别名（init-build 环境检查亦报 `⚠️ cc: 未找到`） | 配方按 R33 从 `tools.build:compiler_executables` dict 取 `c`，调用行显式 `CC=<clang>`（**不用 `${CC}`/`${CFLAGS}` 环境变量**，CI worker 上为空） |
| 7 | `mktemp -d -t poedit.XXXXXX` 若 TMPDIR 未设会落 `/tmp` | 设备 `/tmp` 只读（建目录 `Read-only file system`） | `build()` 显式 `TMPDIR=<conan build 目录>`（实测 `TMPDIR` 生效时 `mktemp -d -t` rc=0）；测试段另置沙箱 `HOME` |
| 8 | **`postats` 真跑失败且静默（交付面缺陷，A 案修复）**：`postats tests/1/in.po` 报 `Error: "potool …/in.po -ft -s" failed`，整脚本仍 **rc=0** | ①同一 musl `getopt` 根因：`scripts/postats` 有 **3 处** `potool $a -ft -s` / `-s` / `-ff -s`（文件在前、选项在后）→ `-ft` 被当输入文件；②**上游吞错形态**：`[ $? -eq 0 ] || { echo "Error: …"; continue; }` 把失败吃掉后循环正常结束 → 脚本退出码 0，属**假绿面**（上游缺陷，已登记 `feedback/upstream-backlog.md` 待修项） | `0004-scripts-postats.patch`：3 处调用改选项前置 + 3 处错误提示串同步（**同一补丁文件内**，未新增补丁）；修复后真跑 **rc=0**、输出 `tests/1/in.po - 5/ 1/9 (55%) -4` 与 `x(100%)x - 5/ 1/9 (55%) -4` 两行统计、0 条 Error（验收读数见下「验证结果」）。上游 `make check` **不覆盖 postats**（只测 potool + poedit），故该缺陷不影响 10/10 结论 |

## 源码修改（补丁 5 个，均 `portability` / platform_only）

| 补丁 | 文件 | 改动 |
|---|---|---|
| `0001-Makefile.patch` | Makefile | `-Werror` 移除（问题 #1） |
| `0002-change-po-charset.patch` | change-po-charset | shebang → `#!/usr/bin/env perl`（问题 #2） |
| `0003-scripts-poedit.patch` | scripts/poedit | shebang → `env bash`；4 处 `potool` 调用改选项前置并同步错误提示串（问题 #2/#3） |
| `0004-scripts-postats.patch` | scripts/postats | shebang → `env bash`；**3 处 `potool` 统计调用改选项前置 + 3 处提示串同步**（问题 #2/#8，同 musl getopt 根因） |
| `0005-scripts-poupdate.patch` | scripts/poupdate | shebang → `env bash`（问题 #2） |

> 生成方式：`refresh-patch --auto`（orig `d0c1ce65f626c8a9` → work `a91a5348063169d4`，5 个文件逐文件 difflib）；5 个补丁已对 pristine 源树 `patch -p1 --dry-run` 全部 OK。
> **披露（编排方裁决 2026-09-24）**：任务卡原写「`-Werror` 是唯一改动点」，经上报后裁决放行可移植性补丁面（shebang / 参数顺序 / locale 环境 shim 三类）；`-Werror` 之外的 4 个补丁均属该裁决授权，PR 正文「已知限制」段同步披露。

## 依赖版本

| 依赖 | 版本 | 角色 | 在档实查（`conan list -r=ohpcd`） |
|---|---|---|---|
| glib | 2.88.3 | 运行期链接 + `pkg-config glib-2.0` | 2.84.0.1.1 / 2.84.0.2 / 2.88.0 / 2.88.0.1 / 2.88.3 / 2.88.3.1 |
| flex | 2.6.4 | tool_requires：生成 `lex.po.c` | 2.6.4 / 2.6.4.2 |
| bison | 3.8.2 | tool_requires：生成 `po.tab.c` | 2.7 / 3.8.2 |
| gettext | 0.22.5 | tool_requires：`msgfmt`（`scripts/poupdate`） | 0.22.5 / 0.22.5.1 |
| pkgconf | 3.0.6 | tool_requires：`pkg-config`（Makefile `$(shell …)`） | 3.0.4 / 3.0.5 / 3.0.6 |

真实组合（`-pr:h`/`-pr:b` 双传绝对路径 profile + `--build=missing`）→ **rc=0，全部命中仓库预编译二进制**（`$TASK_DIR/w0/gate2-conan-install.log`）。

**生成物边界**：`lex.po.c` / `po.tab.[ch]` 既不在 tarball、也不在 git tag，且被上游 `.gitignore`（`lex.po.[co]`、`po.tab.[cho]`）显式忽略 → **flex/bison 生成物不入提交面，源 `po-gram.lex` / `po-gram.y` 入库**。

## 上游测试（N 清点与实测）

- 入口：`make check` → `cd tests && bash test`（`set -e; set -x`，每条用 `diff -u` 断言）
- **N = 10**（上游测试总数，逐条清点自 `tests/test`；4 个 fixture 目录 `1/2/3/4-wrapping`，各以 `in.po` 为输入）：

| # | 用例 | 命令形态 | 结果 |
|---|---|---|---|
| 1 | `TESTING 1 with no filter` | `potool 1/in.po` | PASS |
| 2 | `TESTING 1 with -f no` | `potool -f no 1/in.po` | PASS |
| 3 | `TESTING 1 with -f nt` | `potool -f nt 1/in.po` | PASS |
| 4 | `TESTING 1 with -f nth` | `potool -f nth 1/in.po` | PASS |
| 5 | `TESTING 1 with -f o` | `potool -f o 1/in.po` | PASS |
| 6 | `TESTING 1 with -f t` | `potool -f t 1/in.po` | PASS |
| 7 | `TESTING 2/work.po` | `potool 2/in.po 2/work.po` | PASS |
| 8 | `TESTING 3 with no options` | `poedit 3/work.po` | PASS |
| 9 | `TESTING 3 with -a` | `poedit -a 3/work.po` | PASS |
| 10 | `TESTING 4-wrapping with -p` | `poedit -p 4-wrapping/work.po` | PASS |

- 补丁 + locale shim 后：`make check` **rc=0，TESTING 行数 = 10**（`$TASK_DIR/step2/make-check.log`；沙箱 `HOME=$TASK_DIR/test-home`、`TMPDIR=$TASK_DIR/tmp`、`LC_ALL=C.UTF-8`）。
- 分层实测留档（改动前）：`make check` rc=2（Error 126）止于第 8 条 = 7/10，逐层归因见 `$TASK_DIR/w0/W0-gates.md` 关④。

## 验证结果

```bash
make CC=clang CFLAGS="-O3 -pipe -DNDEBUG -g -Wall" -j1        # rc=0
make install DESTDIR=<prefix> INSTALL=/system/bin/install      # rc=0，5 个文件入 bin/
make check                                                     # rc=0，TESTING 10/10
postats tests/1/in.po                                          # rc=0（修复后），2 行统计、0 Error
```

- **`postats` 修复后真跑（A 案验收读数，2026-09-24）**：

```text
$ postats tests/1/in.po
tests/1/in.po            -     5/  1/9     ( 55%)  -4
x(100%)x                 -     5/  1/9     (55%)  -4
rc=0   Error 行数=0   统计行数=2
```
  （修复前同命令输出 `Error: "potool …/in.po -ft -s" failed` 且 rc 仍为 0 —— 上游吞错，见问题 #8）

- staging 产物：`bin/potool`、`bin/poedit`、`bin/postats`、`bin/poupdate`、`bin/change-po-charset`（与上游 `install` 目标一致；上游无 man 页安装规则）。
- 二进制运行自检：`./potool -h` → `Usage: … FILENAME1 [FILENAME2] [FILTERS] [-s] [-c] [-p] [-h]`，rc=0；无参运行打印 `Input file not specified!`（CRITICAL）属上游正常 CLI 行为。

## 注意事项

- **无 `--version`**：potool 只有 `-h`（用法，stderr，rc=0），test_package 断言须以真实 po 文件处理结果为准，不能只跑 `--version`。
- 上游无共享库产物，按可执行包处理（application），`cpp_info` 不设 libs。
- CI worker 与设备的差异面：worker PATH 含 `/system/bin`（`install` 可直接用）但**同样无 `locale`、无 `/bin/bash`** → locale shim 与 shebang 补丁在 CI 上同为必需。
