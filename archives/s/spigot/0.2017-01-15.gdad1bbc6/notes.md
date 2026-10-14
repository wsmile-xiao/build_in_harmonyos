# spigot 0.2017-01-15.gdad1bbc6 适配笔记

## 编译环境
- 构建系统: autotools（`AM_INIT_AUTOMAKE(foreign)` + `AC_PROG_CXX`）
- 目标平台: HarmonyOS PC / OHOS aarch64（`arch=armv8`, clang 15, libc++）
- 编译日期: 2026-10-04
- 状态: built（本地交叉编译 + 上游测试套件全绿）

## 这是什么包

**spigot ≠ Minecraft Spigot**。它是 Simon Tatham 的 *exact real calculator*：
给一个数学表达式，按任意精度逐位算出结果（spigot 算法），默认一直往 stdout
打数字直到被打断。上游主页 <http://www.chiark.greenend.org.uk/~sgtatham/spigot/>，
源码托管在 <https://git.tartarus.org/simon/spigot.git>，许可证 MIT。

版本串 `0.2017-01-15.gdad1bbc6` 是 `0.<提交日期>.g<commit 前 8 位>` 的形式，
对应上游 commit `dad1bbc6f8fbb588a7a880096d6d3610a29c064f`
（2017-01-15 20:02:32 UTC，"Permit overriding VER on the make command line."）。

## 取源码：为什么不是 chiark 上的 tarball

上游项目页只挂**最新**一份 `spigot-<date>.<hash>.tar.gz`，历史快照早就撤了，
直接 `GET .../spigot-0.2017-01-15.gdad1bbc6.tar.gz` 是 404。所以取的是 Debian
官方归档里对应 commit 的那份：

```
http://deb.debian.org/debian/pool/main/s/spigot/spigot_0.2017-01-15.gdad1bbc6-1.tar.gz
→ HTTP 200, 198888 bytes
→ sha256 = 0ccd92c3f7c2bb39591267437935550839eef7a96bf417c994fd84d38d7283f4
```

**没有拿镜像站糊弄**，并且做了反向取证：把这份 tarball 的源码树和 Simon 自己
git 服务端 clone 下来的 `dad1bbc6` 树对拆：

```
$ git clone https://git.tartarus.org/simon/spigot.git && cd spigot
$ git archive --prefix=spigot/ dad1bbc6f8fbb588a7a880096d6d3610a29c064f | tar -x -C ../gitarch
$ diff -r --brief ../deb-spigot ../gitarch/spigot
Only in .../deb-spigot: debian
```

64 个文件里逐字节相同，只多出 Debian 自己的 `debian/` 打包目录。
提交日期（2017-01-15 20:02:32）与 tarball 的 Last-Modified
（Sun, 15 Jan 2017 20:57:08 GMT）也吻合。

## 依赖（W0 / R36 实测）

| 依赖 | 制品仓 ohpcd | 用途 |
|---|---|---|
| `gmp/6.3.0` | ✅ recipe + ohos-aarch64 二进制 | 大整数运算后端（`--with-gmp`） |
| `ncurses/6.6` | ✅ recipe + ohos-aarch64 二进制 | 交互式行编辑的终端控制序列 |
| `halibut/1.3` | ✅（tool_requires，build 上下文） | 从 `.but` 源生成 spigot.1 / spigot.html |

全部用 `conan download "<ref>" -r=ohpcd --only-recipe` 逐个验过（R35：不许用
`conan list` 判断）。

## 编译步骤

```
1. autoreconf -v -i -f                 # 归档里没有 configure
2. replace_in_file(configure, umask 077 -> umask 022)   # E114/E011
3. autotools.configure()               # --with-gmp
4. autotools.make(args=["-j1"])       # R9：HMDFS 上并行 make 会 EPERM
5. bash test.sh ./spigot               # 上游 1133 个 testcase 真跑
6. autotools.install()                 # bin/spigot + man1 + html
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | **不需要 config.guess/config.sub 补丁** | `configure.ac` 里没有 `AC_CANONICAL_HOST`，`autoreconf -i` 因此不放这两个脚本 | 无需 E007 补丁。实测 `autoreconf -v -i -f` 后目录里确实没有 config.guess/config.sub，configure 直接原生探测成功。**这是本仓库第一个反例**：191 个调 autoreconf 的配方里绝大多数要打 E007 补丁，但判据是 configure.ac 有没有 canonical 宏，不是包名 |
| 2 | 链接期 `undefined symbol: tigetstr / tparm / setupterm` | `ncurses/6.6` 只发 `libncursesw.a`，没有 `libtinfo.a`/`libncurses.a`；而上游 `AC_SEARCH_LIBS(tigetstr, tinfo ncurses)` 只在符号**尚未声明**时才去 -l 候选里找，此刻 `ncurses.h` 还没被 include，所以两个候选都失败、什么也不加。但 `main.cpp` 仍然用这些函数（`AC_CHECK_HEADERS([ncurses.h])` 是成功的） | `autotools.configure(args=["LIBS=-lncursesw"])`（configure 的 precious variable 赋值）。探测结果从 `no` 变成 `none required`，`tiparm` 也从 `no` 变 `yes`。`nm --defined-only libncursesw.a` 确认 tigetstr/tparm/setupterm/tiparm 全在里面 |
| 3 | `make install` 会死在 `man1_MANS` | 归档只带 `.but` 文档源，不带生成好的 `spigot.1`/`spigot.html`；生成规则被包在 `if HAVE_HALIBUT` 里，靠 `AC_CHECK_PROG([HALIBUT])` 决定 | `tool_requires("halibut/1.3")` 把 halibut 放进构建环境 PATH。实测 `configure` 报 `checking for halibut... yes`，`make` 自动跑 `halibut --man=spigot.1 ...` 和 `halibut --html=- ... \| perl -pe ...` |
| 4 | 版本号显示 `unidentified build` | `version.h` 是 `#ifndef VER` 的默认值 | 上游 commit dad1bbc6 加的就是"允许 make 命令行覆盖 VER"，用 `tc.extra_cxxflags` 传 `-DVER='"0.2017-01-15.gdad1bbc6"'` |
| 5 | `configure` 报 `umask 077` 相关失败 | HMDFS 权限模型下 `(umask 077 && mktemp)` 建的目录当前进程写不进去 | build() 里 `replace_in_file(..., strict=False)` 换成 022（htop / bwm-ng / cproto 同一个坑） |
| 6 | 差点顺手加 `tool_requires("perl/5.42.2")` / `m4/1.4.19` | 看着像"补齐 autotools 工具链" | **实测会炸**：这两个在 ohos-aarch64 没有可用预编译二进制，会被拉源码构建并失败（perl 卡在 `pod/perl5422delta.pod`，m4 卡在 `make check`）。本仓库 191 个调 autoreconf 的配方里 **98 个是纯系统工具路线**，跟着走即可——CI 构建机上 autoconf/automake/m4/perl 本来就有（否则 aclocal 这种 perl 脚本跑不起来） |

## 源码修改

**无补丁。** `patches: []`。

- `configure`（autoreconf 生成物）：`umask 077` → `umask 022`，在 build() 里用
  `replace_in_file` 改，不落成 patch 文件（R6：生成文件修改不产补丁）。
- 其余源码零改动。

## 依赖版本

- gmp/6.3.0、ncurses/6.6（都是制品仓已发布的 ohos-aarch64 静态包）
- halibut/1.3（tool_requires，build 上下文工具）

## 验证结果

### 上游自带测试套件（build() 阶段真跑）

一次干净的 `conan create`（先 `conan remove "spigot/0.2017-01-15.gdad1bbc6" -c`
清掉缓存二进制，强制全量重建）耗时 321s，rc=0：

```
$ conan create . -pr:h=ohos-aarch64-lkyz -pr:b=default --build=missing
spigot/0.2017-01-15.gdad1bbc6: Calling source() in .../s
spigot/0.2017-01-15.gdad1bbc6: Calling generate()
spigot/0.2017-01-15.gdad1bbc6: Calling build()
spigot/0.2017-01-15.gdad1bbc6: Calling package()
======== Launching test_package ========
```

configure 的关键探测结果：

```
checking for halibut... yes
checking for main in -lgmp... yes
checking for library containing tigetstr... none required
checking for tcsetattr... yes
checking for tiparm... yes
```

上游 1133 个 testcase：

```
$ bash test.sh ./spigot
---- general info
Program under test:
| ./spigot
Version dump:
| spigot, 0.2017-01-15.gdad1bbc6
|   big integer provider: gmp
|   fd literals (cfracfd:F, baseNfd:F): supported
---- core tests
---- fd tests
---- results
pass 1133
fail 0
total 1133
$ echo $?
0
```

1133 个 testcase 全过，0 失败。覆盖常量 70+ 位精确值、zeta/erf/LambertW、
`algebraic()` 代数数解、对数族（含 dyadic 有理回退）、度制三角、let 绑定、
2/7/16/36/60 进制、printf `%a/%e/%f/%g` 与宽度标志组合、`ieee:` 输入、
`baseNfile:`/`cfracfd:` 等文件字面量、tentative output。

`big integer provider: gmp` 这一行是重点：它证明 GMP 后端真的编进去了，而不是
静默回退到 spigot 自带的慢速内部大整数实现（Debian 专门为此写了
`debian/tests/bigint-provider` autopkgtest）。

### 产物

```
$ file spigot
ELF 64-bit LSB pie executable, ARM aarch64, interpreter /lib/ld-linux-aarch64.so.1
$ readelf -d spigot | grep NEEDED
 0x0000000000000001 (NEEDED)  Shared library: [libc.so]
```

GMP 与 ncurses 都**静态链进**二进制，唯一的动态依赖是平台 libc.so。

`make install` 装出三样：

```
bin/spigot
share/man/man1/spigot.1
share/doc/spigot/spigot.html
```

### test_package（消费者视角，40 项断言）

期望值**逐字取自上游 `test.sh`**（用脚本按片段定位后原样搬运，不是手抄），
另外 2 项是能力上报断言：

- `spigot --version` 以 `spigot, ` 开头
- `spigot --version` 报告 `big integer provider: gmp`

38 条数值断言覆盖：`pi`/`eulergamma`/`zeta(2)`/`zeta(3)` 的 70 位精确值、
上游 exactness 回归用例 `(sqrt(2)-sqrt(2))+sqrt(3)` 与 `sin(pi)+sqrt(2)`、
黄金比例 `algebraic(0,2,-1,-1,+1)`、连分数 `1;2,3`、
`W(-1/e)+sqrt(2)`、`erf(0)`/`erfc(0)`/`Phi(0)`、`inverf(0.99)`、
`log(0.66)`、`log2(2^456)`、dyadic `log(4,2)`、`log(6,12)` 的有理回退、
`1/2 - pi/1e80`、let 绑定、`-R 4/-9`、进制 2/16/36、
`--printf=%.10a`/`%e`/`%.17g`/`'% 50.10a'`、`cosd/asind/atan2d`、
`(+2)^(-10/4)` 与 `(+2)^(1/4)`。

```
[summary] pass=40 fail=0 total=40
test spigot 0.2017-01-15.gdad1bbc6: PASS
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, ..., "discovered": 40, "passedCount": 40}
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", ..., "discovered": 1133, "executed": 1133, "passed": 1133, "failed": 0, "skipped": 0}
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/spigot` | aarch64 OHOS 可执行文件 |
| `share/man/man1/spigot.1` | halibut 从 `manpage.but` 生成 |
| `share/doc/spigot/spigot.html` | halibut 从 `defs.but`+`manual.but`+`manpage.but` 生成 |

## 注意事项

- **不要给这个包加 `tool_requires("perl/5.42.2")` 或 `m4/1.4.19`**：源码构建会失败（见上表 #6）。
- `spigot.html` 的生成规则里用了 `perl -pe` 做一处把 `<em>` 换成红色 `<span>`
  的后处理（纯排版）。CI 构建机有 perl（automake 的 `aclocal` 本身就是 perl
  脚本），实测通过。
- 上游 `test.sh` 依赖 bash 的进程替换 `<(...)` 和 `$'...'`，且末尾 fd 测试依赖
  perl；必须用 bash 跑，不能用 OHOS 的 `/system/bin/sh`（mksh）。
- `-DVER` 走的是 `extra_cxxflags`（即 CXXFLAGS）而不是 CPPFLAGS，因为
  `AutotoolsToolchain` 的 CPPFLAGS 已被 `AutotoolsDeps` 占用（放 `-I`），
  覆盖会丢掉 ncurses/gmp 的头文件路径。

---

## 2026-10-11 CI 记录（分支内容恢复 + 平台派活缓存未刷新）

### 1. 分支内容恢复

本 MR 的头分支 `feat/spigot-0.2017-01-15.gdad1bbc6` 在 `wzp780028` fork 上曾被写成
**pd-cxc** 的两个提交（`b4049d6ec9`），分支里没有任何 spigot 文件，于是 CI 的 L0n（R40
「分支名必须等于 包名-版本号」）每轮必然失败。pd-cxc 本身没有丢：同一提交由 MR #15272
（分支 `feat/pd-cxc-0.5.2`）承载。

本次在最新 `main`（`b644cbf8ed`）上把 `archives/s/spigot/0.2017-01-15.gdad1bbc6`
重建为单提交 `e8e2b410f8` 并 force-push，使本 MR 只包含 spigot 包。

### 2. 本地同源门禁（全绿）

```
G0_RESULT=pass   KC_RESULT=pass   JC_RESULT=pass
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: spigot --version OK
L4_RESULT=pass: no patches
L5_RESULT=pass: bin/ has content
HMBS_TEST_PACKAGE_RESULT   = {"executed": true, "passed": true, "discovered": 40, "passedCount": 40}
HMBS_UPSTREAM_TEST_RESULT  = {"status": "passed", "discovered": 1133, "executed": 1133, "passed": 1133, "failed": 0}
```

### 3. 平台侧派活仍用旧的变更包列表（导致「No packages to build」）

恢复内容之后，平台 API 的**文件列表**已经刷新正确（`GET /pulls/15273/files` = 10 个
`archives/s/spigot/…`），但 **CI 派活**仍传旧包路径（构建 #84665 @17:49、#84776 @19:56
两次完全相同）：

```
hCI_PACKAGES="archives/p/pd-cxc/0.5.2" CI_BRANCH="feat/spigot-0.2017-01-15.gdad1bbc6" CI_PR_NUMBER="15273"
o[step] CI_PACKAGES received: archives/p/pd-cxc/0.5.2
o[warn] Path in CI_PACKAGES has no conanfile.py: archives/p/pd-cxc/0.5.2
o[error] No packages to build
```

即：force-push 改写了分支内容，但该 MR 的「变更包列表」缓存没有失效（`CI_PR_NUMBER=15273`
说明 PR 上下文本身是对的）。已作为「缺陷 5」记入仓库 issue #3919：
<https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3919>

**在平台刷新该缓存之前，本 MR 的 CI 无论 `/rebuild` 多少次都会停在
「No packages to build」——与 spigot 的代码无关。**
