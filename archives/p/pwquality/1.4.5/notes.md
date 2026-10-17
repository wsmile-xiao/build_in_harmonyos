# pwquality (libpwquality) 1.4.5 适配笔记

## 概述

libpwquality 是密码质量检查库（Linux 发行版 `pam_pwquality` 的底层），提供
`pwquality_check` / `pwquality_generate` / `pwquality_strerror` 等 API，
并附带两个命令行工具 `pwscore`（评分）与 `pwmake`（生成口令）。

- 上游：https://github.com/libpwquality/libpwquality
- 版本：1.4.5（注意 Git tag 名为 `libpwquality-1.4.5`，带前缀）
- 构建系统：**autotools**（release 资产含预生成 `configure`）
- 许可：GPL-2.0-or-later
- 编译日期：2026-09-16
- 状态：built

## 交付物

| 类型 | 文件 |
|---|---|
| 库 | `lib/libpwquality.so*` |
| 头 | `include/pwquality.h` |
| pkg-config | `lib/pkgconfig/pwquality.pc` |
| 工具 | `bin/pwscore`、`bin/pwmake` |

## 依赖（本包关键信息）

| 依赖 | 性质 | ohpcd | 处置 |
|---|---|---|---|
| **`cracklib`** | **默认必需** | ✅ 2.10.3 | `requires()` + `AutotoolsDeps` |
| ~~`libintl`~~ | NLS 需要 | ⚠️ 0.26.1 但**不能用于链接** | **已移除依赖**（见下方「实测订正一」）|
| PAM | 可选（`enable_pam=check`）| ✅ linux-pam 1.7.2 | **显式 `--disable-pam`** |
| Python bindings | 上游默认 **yes** | — | **显式 `--disable-python-bindings`** |

### 为什么 cracklib 是**硬**依赖

`configure.ac` 里：

```sh
AS_IF([test "x$enable_cracklib_check" != "xno"], [
    AC_CHECK_HEADERS([crack.h],[
        AC_CHECK_LIB([crack], [FascistCheck], LIBCRACK="-lcrack" LIBS="$LIBS", LIBCRACK="")
        ...
    ])
    if test "x$LIBCRACK" = "x" ; then
        AC_MSG_ERROR([No or unusable cracklib library])   # ← 直接报错退出
    fi
])
```

即**找不到 cracklib 就 configure 失败**，不能像 PAM 那样"没有就跳过"。
所以配方必须 `requires("cracklib/2.10.3")` 并接 `AutotoolsDeps`
（否则 `AC_CHECK_LIB` 拿不到 `-I/-L/-l`，同样报 `No or unusable cracklib library`）。

### 为什么 PAM 与 Python bindings 都关掉

- **PAM**：`pam_pwquality.so` 属系统 *secure-lib* 目录、且需消费方 PAM 配置，
  超出本包范围；本包的目标是库 + `pwscore`/`pwmake`。关掉同时也少一个依赖。
- **Python bindings**：上游默认 `yes`，但为一个小 binding 引入 conan `python`
  依赖不划算；Python 侧在本仓单独覆盖。

## OHOS 适配一：config.guess / config.sub（重点）

上游自带的是 **2018 世代**辅助脚本（`timestamp='2018-08-29'`），而仓内强制的
`scripts/patch-autotools-ohos.pl` 是按**新版格式**写的，实测对本包**只打中 1/5**：

```
[warn] Could not find __ANDROID__/LIBC=android in config.guess
[warn] Could not find android-linux in config.sub
[warn] Could not find linux-uclibc pattern in config.sub
Score: 1/5      ❌ Some patches may have failed.
```

补丁后 `./config.guess` 仍报 `unable to guess system type`，`config.sub` 还会把
`aarch64-unknown-linux-ohos` 误规范成 `aarch64-unknown-linux-gnu-ohos`。

**根因**（两处世代差异）：

| 差异 | 新版 | 2018 旧版（本包）|
|---|---|---|
| `config.guess` 输出机制 | 统一 `GUESS=` 变量 + 末尾 echo | **各分支自行 `echo` + `exit`** |
| `config.sub` 的 `linux-*` 模式 | 含 `linux-ohos*` 等 | **无 `ohos`** |

**修法（`patches/0001-config-guess-sub-ohos.patch`，按旧版格式）**：

1. `config.guess`：在 `case "$UNAME_MACHINE:$UNAME_SYSTEM:..."` 起始处插入
   自行 echo+exit 的分支：

```sh
    *:HarmonyOS:*:*)
	echo ${UNAME_MACHINE}-unknown-linux-ohos
	exit ;;
```

2. `config.sub`：在 **`maybe_os` 列表**与 **os 合法性列表**各加 `linux-ohos*`：

```diff
-			| linux-newlib* | linux-musl* | linux-uclibc* | uclinux-uclibc* \
+			| linux-newlib* | linux-musl* | linux-uclibc* | linux-ohos* \
+			| uclinux-uclibc* \
```

**实测验证**：

```
$ sh ./config.guess
aarch64-unknown-linux-ohos          ✓
$ sh ./config.sub aarch64-unknown-linux-ohos
aarch64-unknown-linux-ohos          ✓
$ sh ./config.sub aarch64-linux-ohos
aarch64-unknown-linux-ohos          ✓
```

> 这与本仓「**禁止用 `--build`/`--host` 绕过 config.guess**」的铁律一致
> （见 `patch-autotools-ohos.pl` 头部注释）。

## OHOS 适配二：`umask 077` → `022`（HMDFS 陷阱）

`configure` 内有两处 `umask 077`（`config.status` 的 here-doc 继承同样文本）。
`config.status` 会在**构建目录**（非 `TMPDIR`）建 `confXXXXXX` 临时目录并往里写
`subs*.awk`，HMDFS 拒绝写入 700 目录 → `Permission denied`。
**cracklib 配方踩过同一个坑**，故本配方在 `build()` 内同样把 `umask 077` 全部
放宽为 `022`（`configure` 与 `config.status` 同步修复）。

## 上游测试：结构性缺失（六项证据，非环境不可用）

**结论：上游未提供任何测试用例，`make check` 结构性无可跑内容。**
这不是"环境缺依赖导致跑不了"，故不可与"依赖缺失跳过"混为一谈。2026-09-17
实测六项独立证据：

| # | 证据 | 实测命令与结果 |
|---|---|---|
| ① | **无测试目录** | 顶层 `SUBDIRS = po src doc`（条件追加 `python`）；全树无 `tests/`、无 `check/` |
| ② | **全树无测试声明** | `grep -rnE '^\s*(TESTS\|check_PROGRAMS\|check_SCRIPTS\|check_LTLIBRARIES\|dist_check_SCRIPTS\|TEST_EXTENSIONS)' --include=Makefile.am` → **0 命中** |
| ③ | **configure.ac 无测试基础设施** | 无 `AC_CONFIG_TESTDIR`、无 `--enable-test`、无 `TESTS` |
| ④ | **实跑 `make check`** | 逐子目录输出 `Nothing to be done for 'check'`（po / src / doc / doc/man 全同），`rc=0` |
| ⑤ | **无测试源文件** | `find` 全树 `*.t` / `test*` / `*test*` / `check*` 仅得两枚：`m4/progtest.m4`（autoconf 宏，非测试）、`src/check.c`（**libpwquality 主力 API 实现**，文件名含 check 但内容是质量检查逻辑）|
| ⑥ | **python 绑定无测试** | `python/` 仅 `setup.py(.in)` + `pwquality.c` + `Makefile.am`，无任何 py 测试 |

属"**上游未提供**"，**非环境不可用** —— `MANIFEST.yml` 内
`upstream_test_in_build: false` 已如实标注，并在注释中附上述证据。

> 特别说明证据 ⑤ 的易误判点：`src/check.c` 名字含 "check"，乍看像测试程序，
> 实为**公开 API 的主体实现**（`pwquality_check()` 等）；`m4/progtest.m4` 是
> autoconf 的编译器探测宏。二者都不构成测试用例。

因此本包的验证责任全部落在 **test_package 的真实 API 测试**上（见下）。

## 消费者测试（test_package）

`test_package/test_pwquality.py` 用 **C 编译器链接打包的头与库**编译并运行一个
真实 C 程序（与 cracklib test_package 同思路），全部为真实 API 断言（R34）：

| 组 | 断言 |
|---|---|
| 打包物 | `include/pwquality.h`、`lib/libpwquality.so*`、`lib/pkgconfig/pwquality.pc` 均存在 |
| **pkg-config 契约** | `--modversion` = **1.4.5**；`--libs` 含 `-lpwquality` |
| 默认设置 | `pwquality_default_settings()` 非 NULL |
| **整型设置往返** | `set_int_value(PWQ_SETTING_MIN_LENGTH, 12)` → `get_int_value` 读回 12 |
| **强密码通过** | `pwquality_check("Str0ng!Password#2024", ...)` 返回 **score >= 0** |
| **弱密码拒绝** | `pwquality_check("ab", ...)` 返回负值，且 `pwquality_strerror` 产出**非空**消息 |
| **generate→check 闭环** | `pwquality_generate(pwq, 64, &pw)` 生成后**回灌** `pwquality_check` 须通过 |
| 资源释放 | `pwquality_free_settings` |
| **CLI 工具真实执行** | `pwscore`（stdin 喂密码得分数，输出非空）、`pwmake 64`（产出密码长度 ≥ 8）|

## 验证结果

```
conan create archives/p/pwquality/1.4.5 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
→ exit=0
```

| 项 | 实测结果 |
|---|---|
| `conan create` | **exit=0**，Package created（`c14fb81001f31c9dae0f0af376cbe5144e3b2420`）|
| umask 修复 | `widened umask 077 -> 022 in configure (HMDFS)` |
| 交付物 | `libpwquality.so*`、`include/pwquality.h`、`lib/pkgconfig/pwquality.pc`、`bin/pwscore`、`bin/pwmake`、3 个 man 页 |
| pkg-config 契约 | `--modversion` = **1.4.5**；`--libs` 含 `-lpwquality` |
| 消费者程序 | 编译并运行通过：MIN_LENGTH 往返=12；强密码 **score=100**；过短密码拒绝（"shorter than 12 characters"）；生成密码长度 14 且**回灌校验 score=43** |
| CLI 工具 | `pwscore` 长度检查触发（rc=1）；`pwmake` 用法路径（无参 rc=3、非数字 rc=4）|
| 消费者测试 | `pwquality 1.4.5 consumer API: PASS` |

### 实测订正一：移除 libintl 依赖（ohpcd 的 libintl 无法用于链接）

初版 `requires("libintl/0.26.1")`（因 `AM_GNU_GETTEXT([external])`）导致 configure 失败：

```
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: gettext
... dgettext / dcgettext / ngettext / dngettext / dcngettext
    bindtextdomain / textdomain / bind_textdomain_codeset
configure: error: C compiler cannot create executables   ← 误导性报错
```

**根因**：ohpcd 的 `libintl.so.8` 把 `gettext`/`dgettext`/`bindtextdomain` 等
**全部列为未定义符号**（`nm -D -u` 实测），即该库自身不提供这些实现；
`AutotoolsDeps` 注入 `-lintl` 后 lld 因 `--no-allow-shlib-undefined` 直接报错。

**处置**：既然本构建本就 `--disable-nls`（不需要 NLS），**直接移除 libintl 依赖**。
注意真正的错误被 configure 包装成 `C compiler cannot create executables`，
必须看 `config.log` 才能发现是链接期的 `undefined reference`。

### 实测订正二：词典检查依赖**运行时数据**（cracklib 词典未随包交付）

库级功能测试原用默认设置（`dict_check=1`）跑强密码，失败：

```
FAIL: strong password rejected: score=-22 msg=The password fails the dictionary check
FAIL: pwquality_generate rc=-24
/__pkg_prefix__/share/cracklib/pw_dict.pwd: No such file or directory
```

**根因**：`dict_check` 会调 cracklib 的 `FascistCheck`，而它需要**运行期已编译的
词典**（`pw_dict.pwd`/`.pwi`）。本仓 cracklib 包**只交付头与库、不含词典**
（实测 `find` 无 `pw_dict*`），故：

- `PWQ_ERROR_CRACKLIB_CHECK`（**-22**）= 词典缺失；
- `PWQ_ERROR_GENERATION_FAILED`（**-24**）= `pwquality_generate` 因候选密码
  过不了词典检查而级联失败。

这属**环境数据依赖缺口，非库缺陷**。处置：消费者测试**显式探测并记录**该行为
（`dict_check=1` 时断言必须得到 -22），随后 `set_int_value(PWQ_SETTING_DICT_CHECK, 0)`
关闭词典检查以验证其余功能（强密码 score=100、生成密码可回灌验证）。

> 附注：报错里出现的 `/__pkg_prefix__/share/cracklib/pw_dict` 中含 `__pkg_prefix__`
> 占位符——实测该字符串来自 **pwquality 自身**的库（编译期生成的默认词典路径），
> cracklib 库内无此串。

CLI 工具同理：`pwscore` 的**长度检查先于词典检查**（故可用过短密码验证真实代码路径），
`pwmake` 的**用法路径不碰词典**（无参 → rc=3、非数字 → rc=4）；两者的完整生成/评分
路径在当前环境因缺词典不可达，已如实记录。

## 注意事项

1. **优先取 release 资产**（`.tar.bz2`，含预生成 `configure`）；codeload 的
   `/archive/refs/tags/*.tar.gz` **不含** `configure`，需 autoreconf；
2. **cracklib 是硬依赖**，必须 `requires()` + `AutotoolsDeps`，否则 configure 直接失败；
3. **不要用 `--build`/`--host` 绕过** —— patch `config.guess`/`config.sub`
   （且本包的 2018 世代需按**旧版格式**打，仓内脚本只打中 1/5）；
4. **`umask 077` 须放宽为 022**（HMDFS 拒绝向 700 临时目录写入）；
5. `make -j1`（R9：HMDFS jobserver fifo EPERM，见 E074）；
6. 交付后剔除 `*.la`（libtool 包装脚本里硬编码 libdir，消费时会报错）。
