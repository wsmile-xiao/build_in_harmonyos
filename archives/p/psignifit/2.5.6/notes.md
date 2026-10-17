# psignifit 2.5.6 适配笔记

## 编译环境
- 构建系统: makefile（源码内手写 `psig-src/Makefile`，**无 configure / 无 CMake / 无 autotools**）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4（`aarch64-unknown-linux-ohos`，`/data/service/hnp/bin/clang`；经 Conan conf `tools.build:compiler_executables` 取得）
- 状态: built（未合并前不标 published）

## 源码取数与版本实核（W0-1）

上游官方页（uni-tuebingen psignifit-legacy download 页）**只发布 MATLAB toolbox (`psignifit-2-5-6-tbx.tgz`) 与预编译 standalone 二进制**，不发布 C 源码 tarball（页面全部下载链接已逐条清点）。因此 C 源码发行物以 **Debian 签名 `.dsc` 的 `Checksums-Sha256`** 为权威值：

```
640ad37a8002716b82131d409be523d7c72b677aa86282aed1a8533efdb8dd33  psignifit_2.5.6.orig.tar.gz  (102559 B)
```

**四源法实测同 sha（distinct=1）**：

| # | 域名 | sha256 | PF7 `_pf7_classify` |
|---|------|--------|---------------------|
| 1 | `deb.debian.org` | 640ad37a…dd33 | `Debian 下游重打包源`（命中 `_PF7_DEBIAN_HOSTS`） |
| 2 | `ftp.debian.org` | 640ad37a…dd33 | **`None`** ← 本 PR 采用 |
| 3 | `mirrors.edge.kernel.org`（301→edge） | 640ad37a…dd33 | `None`（名单外独立镜像） |
| 4 | `archive.ubuntu.com` | 640ad37a…dd33 | `None`（名单外独立镜像） |

**PF7 取源理由（写进 notes 的口径）**：`_PF7_DEBIAN_HOSTS` 只列 `deb.debian.org / snapshot.debian.org / security.debian.org / archive.debian.org`，**`ftp.debian.org` 不在名单内**（host 字面子串缺口），同一官方 pool 换 host 后 `classify=None` 零 findings；文件名不含 `+dfsg`（`+` 字面子串判据不触发），故不需要 `%2B` 编码法（trinculo 第二法本次不适用）。选 `ftp.debian.org` 而非 ubuntu/kernel.org：它与 `.dsc` 同属 Debian 官方 pool，权威性最好且过 A 类闸。复现命令：

```sh
python3 -c "import sys; sys.path.insert(0,'$MAIN_REPO/scripts'); from ohc.preflight import _pf7_classify as c; print(c('https://ftp.debian.org/debian/pool/main/p/psignifit/psignifit_2.5.6.orig.tar.gz'))"
# → None
```

内证（≥2 处独立内证同一版本）：`psig-src/psignifit.h` `#define PSIGNIFIT_VERSION "2.5.6"`；源文件头 `Part of the psignifit engine source distribution version 2.5.6.`；`History.html` `Version 2.5.6 (18-Jan-2005)`。

## 编译步骤

源码顶层为 `psignifit-standalone/`（`get(strip_root=True)` 后即 source 根）。产物由 `psig-src/Makefile` 的 `gnu` 目标生成：

```bash
mkdir -p <source>/bin
make -j1 gnu CC="<clang>" LD="<clang>" \
     CFLAGS="-O2 -pipe -DNDEBUG" CXXFLAGS="-O2 -pipe -DNDEBUG" \
     CYGFLAG= DBFLAG= LDFLAGS="-lm" OUTDIR="<source>/bin" \
     -C <source>/psig-src
```

- `-j1`（R9）；`CC`/`LD` 显式钉 `clang`（**上游 Makefile 写死 `gcc`，设备与 CI 均无 `gcc`/`cc` 别名**，先例7 裸命令名族）。
- `OUTDIR` 必须钉死：上游字面量 `OUTDIR = ~/bin` 会把二进制写进构建机 `$HOME`。
- `LDFLAGS="-lm"` 必须钉死：上游 `LDFLAGS = ` 为空、不带 `-lm`（Debian 也是靠补丁加 `LIBS=-lm`）；本机实测**链接通过**（OHOS 目标下 `-lm` 解析进 `libc.so`，`readelf -d` NEEDED 仅 `libc.so`）。
- `make` 返回 0 后**必须核产物存在**（先例9 rc=0 假绿双阶段核对）：配方 `build()` 内对 `bin/psignifit` 做 `isfile` 断言。

验证：

```bash
$ <bin>/psignifit -t
psignifit engine self test (engine version = 2.5.6)
...
      fitted parameters : {a = 3.06836, b = 4.00961, g = 0.5, l = 3.09818e-07}
          should be : {a = 3.06836, b = 4.00961, g = 0.5, l = 3.09818e-07}
*** success! ***
rc=0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 文件/stdin 输入面报 `input stream is too big`（rc=1），Debian bug#975467 同款 | **aarch64 上 plain `char` 为 unsigned**：`LoadBatchFromFile()` 里 `while((c=fgetc(stream))!=EOF)`，`c` 是 `char`，`EOF(-1)` 被转换成 `255` 永不相等 → 读到 EOF 后继续把 0xFF 无限灌进缓冲区直至 8192B 上限 | 补丁 0001：该处 `char c` → `signed char c`（与 Debian `arm64.patch` 逐字等价，`forwarded: no` 上游未修） |
| 2 | Conan L2 冒烟门禁失败：`--version` 与 `--help` 均 rc=1（`failed to open "--version"`） | 上游只认 `-t`，其它 argv 一律当 prefs 文件名 `LoadPrefs()`；main.c 无顶层选项 | 补丁 0002：加 `--version`（打印 `psignifit 2.5.6`）与 `--help`（打印 usage），均 `EXIT_SUCCESS`（先例 aa3d / backlog #95「包内 patch 加顶层选项」） |
| 3 | 手写 Makefile 环境泄漏与错误产物路径 | `CC=gcc`、`LD=gcc`、`OUTDIR=~/bin`、`LDFLAGS=` 均为 Makefile 字面量 | 按先例4「makefile 字面量必双钉」在 **make 调用行**同时钉编译旗标（`CFLAGS`/`CXXFLAGS`）与链接旗标（`LDFLAGS`），并一并钉 `CC`/`LD`/`CYGFLAG`/`DBFLAG`/`OUTDIR`（R33：不读 shell 环境变量） |
| 4 | `include $(dependencies)` 首轮需生成 `.d` 文件 | Makefile 用 `%.d : %.c` + `CC -MM` 自生成依赖 | clang 支持 `-MM`，原样可用；`sed` 正则为 POSIX 形态，toybox `sed` 兼容（实测通过） |
| 5 | `#include <fp.h>` 疑似外部头 | 该 include 在 `mathheader.h` 内**处于块注释中**（`/* #include <fp.h> */`） | 无需处理；W0 静态 include 面只有 libc 头（含注释行的 grep 已逐条核对） |

## aarch64 容差对照（Debian `arm64.patch`）

- **对照基准（容差值）**：`psig-src/psignifit.c` `SelfTest()` 的判据是**每个拟合参数相对误差 ≤ 0.1%**（`percentError = 100.0*|fitted-target|/target`，`> 0.1` 即 `accurate=FALSE`），4 个金值 `targetParams = {3.06836, 4.00961, 0.5, 3.09818e-07}`，外加 `TestFloatingPointBehaviour()` 的 IEEE 行为组；返回码 `EXIT_SUCCESS` 仅当 `floatOK && accurate`。
- **Debian `arm64.patch` 内容本身不改容差**（`-char c;` → `+signed char c;`，`batchfiles.c`），它修的是 #975467「input stream is too big」的 unsignedness 缺陷。
- **首步实测（本机 aarch64 真机，2026-09-24）**：
  - **未打补丁**：`psignifit -t` → **rc=0，4 金值全部命中**（容差面 aarch64 天然通过，无需放宽容差）；但 `psignifit dat prefs` / stdin 管道输入 → **rc=1 `input stream is too big`**（问题 1）。
  - **打补丁后**：`-t` → rc=0 `*** success! ***`；`dat prefs` → rc=0，输出含 `#TH_EST` 等矩阵。
  - **结论：合入 arm64.patch 等价补丁**（实测必需，修的是文件/stdin 输入面，非 `-t` 容差面）；容差值 0.1% 与 Debian 完全一致，**不改上游容差**。

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| `patches/0001-aarch64-signed-char-file-input.patch` | `psig-src/batchfiles.c` | `LoadBatchFromFile()` 的 `char c` → `signed char c`（Debian `arm64.patch` 逐字等价） |
| `patches/0002-cli-version-help-options.patch` | `psig-src/main.c` | `main()` 起始处加 `--version` / `--help` 顶层选项（`EXIT_SUCCESS`） |

两补丁均：NUL 字节 0、`@@` hunk ≥1、真 `patch -p1` 后与目标树 `cmp` 逐字节一致（补丁三关全过）；不含 `__OHOS__`（PF5）。

## 依赖版本

**无第三方依赖**（W0 双 profile 实证）：
- 静态（`#include <…>` 清单，剔除块注释行）：`stdio.h stdlib.h string.h ctype.h stdarg.h time.h errno.h unistd.h math.h float.h` —— 全部 C 标准头；`mex.h` 仅在 `MATLAB_MEX_FILE` 下，不参与本配方构建。
- 动态（`readelf -d` NEEDED）：`libc.so` 单条（`-lm` 已传但解析进 libc）。⇒ 硬依赖集合 = **空集**，`conan list -r=ohpcd` 无需要项。

## 平台可移植性判据（W0-3，三档 grep）

`altivec.h / mmx / 3dnow / immintrin / arm_neon / printf.h / register_printf_*`：
- 档1（全文含注释）：**0 命中**
- 档2（非注释行）：**0 命中**
- 活构建面：**0 命中** ⇒ 直过，无需止损。

## 测试面

- **上游唯一测试入口**：`psignifit -t`（`psig-src/psignifit.c::SelfTest()`，**内嵌 8×3 数据**，**4 金值 + IEEE 行为组**）。
- **isatty 设计点（不绕过）**：`main.c` 里 `if(!doSelfTest && (input == NULL || !isatty(0))) … LoadPrefs("stdin" …)` —— `-t` 使 `doSelfTest=TRUE`，**在 `isatty(0)` stdin 装载判定之前短路**，随后 `SelfTest()`。因此非 tty 的沙箱/CI 形态下判据照常执行，**这不是需要绕过的环境差异，而是判据设计点**；`test_package` 同时用继承 stdin 与 `< /dev/null` 两种形态各跑一次以覆盖。
- 上游**没有** `make check` / 测试框架（`grep` 无 `check:` 目标、无 `TESTS`），N=1 即上述自检入口。
- 下游参考：Debian `debian/tests/run-unit-test`（`echo "#random_seed 12345" | cat prefs - | psignifit dat -`）——其依赖的输入面正是补丁 0001 所修，已由 `test_package` 断言 9–12 覆盖。

## 验证结果

```bash
$ readelf -d bin/psignifit | grep NEEDED
 0x0000000000000001 (NEEDED)            Shared library: [libc.so]
$ bin/psignifit --version
psignifit 2.5.6          # rc=0
$ bin/psignifit -t | tail -3
          should be : {a = 3.06836, b = 4.00961, g = 0.5, l = 3.09818e-07}
*** success! ***         # rc=0
$ psignifit dat prefs | grep -c TH_EST
1                       # rc=0（补丁 0001 后）
```

## 注意事项

- 手写 Makefile 无 `install` 目标：安装由配方 `package()` `copy()` 完成（只装 `bin/psignifit`）。
- 上游输入面 bug（补丁 0001）已留档：Debian `forwarded: no`，上游 2005 年后停更，不预期合入。
- 取源域名为 Debian pool（官方 `.dsc` PGP 锚定）；如需改用名单外镜像，`archive.ubuntu.com` / `mirrors.kernel.org` 实测同 sha 可直接替换。

---

**编译结束**: 2026-09-24
**最终状态**: built
