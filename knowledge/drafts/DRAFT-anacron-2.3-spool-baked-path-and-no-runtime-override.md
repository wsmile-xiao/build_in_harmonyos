# 裸 Makefile 把**运行时行为路径**烧成编译期宏、且上游不给覆盖口：`PREFIX` 覆盖救不回来，必须补一个环境变量覆盖口

> Draft: `DRAFT-ANACRON-23-SPOOL-BAKE-NO-RUNTIME-OVERRIDE`
> Stem: `anacron-2.3-spool-baked-path-and-no-runtime-override` — pairs with the same-stem `.kv`
> Issue: [#3796](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3796)

## 基本信息

- **ID**: DRAFT-ANACRON-23-SPOOL-BAKE-NO-RUNTIME-OVERRIDE
- **严重度**: 2
- **类别**: build-system, platform, runtime, portability
- **触发工具**: conan|clang|make
- **阶段**: compilation|runtime
- **宿主**: anacron 2.3（任务 14914，2026-10-06）

## 错误特征

第一层错误在**编译期**，且逐字为：

```
make: cc: No such file or directory
make: *** [Makefile:63: gregor.o] Error 127
```

修掉 `CC` 之后，真正暴露本条机制的是**运行时**的两条：

```
anacron: Can't open temporary file: Read-only file system
anacron: Aborted
```

```
anacron: getpwuid() error: No such file or directory
anacron: Aborted
```

以及在缺 `obstack.h` 的系统上：

```
readtab.c:32:10: fatal error: 'obstack.h' file not found
```

关键识别点（决定了这**不是**普通的"构建路径烧死"）：

| 源码位置 | 形态 |
|---|---|
| `Makefile` `ALL_CPPFLAGS` | `-DSPOOLDIR=\"/var/spool/anacron\" -DANACRONTAB=\"/etc/anacrontab\"` |
| `Makefile` `installdirs` | `$(INSTALL_DIR) $(BINDIR) $(PREFIX)$(SPOOLDIR) $(MANDIR)/man5 …` |
| `main()` | `if (chdir(SPOOLDIR)) die_e("Can't chdir to " SPOOLDIR);` |
| `parse_opts()` | 只有 `-t` 覆盖 **anacrontab**，**没有任何开关碰 spool** |
| `runjob.c` | `name = tempnam(NULL, NULL);` |
| `runjob.c` `username()` | `if (ps == NULL) die_e("getpwuid() error");` |

## 根因：区分「构建期路径」与「运行时行为路径」

上游 Makefile 里的路径分两类，**修法完全不同**：

1. **构建期路径**（`CC`、`CFLAGS`、`X11INC` 这类给编译器/链接器用的）——
   make 命令行覆盖即可，**这是已有机制 M18 覆盖的场景**（dmenu 5.4 的
   `make: cc: No such file or directory` + `Error 127` 与本包第一条错误逐字相同）。
2. **运行时行为路径**（`SPOOLDIR` 这种程序跑起来以后要 `chdir()`/打开的目标）——
   make 覆盖**只改变 `install` 的安装落点，运行时读的仍是编译期 `-D` 宏**。
   于是出现死局：把 `PREFIX` 设成可写前缀，装出来的东西位置对了，
   一跑仍然 `chdir` 到编译期那个只读路径。

更麻烦的是上游 `installdirs` 拼的是 `$(PREFIX)$(SPOOLDIR)`：

- 要让安装落点正确 ⇒ `SPOOLDIR` 必须是**相对**路径（`PREFIX` + 相对段）；
- 要让编译宏可用 ⇒ `SPOOLDIR` 必须是**绝对**路径（`chdir()` 绝对定位）。

**两者互斥**。解法是把 `PREFIX` 留成空串，然后 `BINDIR`/`MANDIR`/`SPOOLDIR`/
`ANACRONTAB` 四个绝对路径逐个显式传 —— 双拼退化成 `$(SPOOLDIR)` 本身，
同时编译宏与安装落点保持同一组值。

### 同一条链上的另两个运行时地雷

- **`tempnam(NULL, NULL)` → `P_tmpdir` = `/tmp`（只读）**。
  常规解法是设 `TMPDIR`，但**本平台实测无效**：

  ```
  # 不设 TMPDIR
  NULL,NULL -> /tmp/temp_npNfAM
  # 设 TMPDIR=<可写目录>
  TMPDIR env = .../anacron-prefix-test/tmp
  NULL,NULL -> /tmp/temp_phEhfM        ← 仍然返回 /tmp
  explicit dir -> .../tmp/an_GOmifM    ← 只有显式目录参数才生效
  ```

  这意味着 **E002（/tmp 只读）那条"改 TMPDIR"的解法在这里不成立**，
  属于既有条目没写的另一条解法 ⇒ 按 `create` 申报，不判 `hit`。
  正确修法是 `tempnam(已有可写目录, 前缀)` —— 而 `main()` 已经 `chdir()`
  进了本包自有的 spool 目录，`tempnam(".", "an")` 即可。

- **`getpwuid()` 返回 NULL ⇒ 上游 `die_e()` 中止整轮运行**。
  `/etc/passwd` 在本平台**存在**（15382 B），但 app/sandbox uid
  （本例 `20020084`）刻意不在其中：

  ```
  $ python3 -c "import pwd,os; print(pwd.getpwuid(os.getuid()))"
  FAIL: KeyError 'getpwuid(): uid not found: 20020084'
  ```

  该地址只用于填充邮件 `From:`/`To:` 头这类信息性字段，把「失败即中止」
  收窄为「退回 `$LOGNAME` → `$USER` → `anacron`」即可。

### 第三层：musl 没有 `obstack.h`

`readtab.c` 用 `#include <obstack.h>`（尖括号），musl/HarmonyOS 不提供。
**⚠ 口径更正（W4 P1-2）**：制品仓**并非没有** —— 按 4 个精确名
`obstack`/`gnulib`/`libiberty`/`gnu-obstack` 检索确实 0 命中，但**漏检了
`musl-obstack/1.2.3`**：该包在库（`archives/m/musl-obstack/1.2.3/`、
`_index.yaml` 在册 uploaded、`status: built`），并被 `dwarves/1.30:56`、
`dwz/0.16:39`、`box64/0.4.4:56`、`elfutils/0.195.1:119` 四个配方直接 `requires`。
处置：**本包仍选 vendor**（application 包免引入 shared 依赖与 SONAME 打包面），
而非因为查不到。取 **GNU C Library** 的 `obstack.h`+`obstack.c`（经 gcc-mirror
的 `include/` 与 `libiberty/` 取得，LGPL-2.1-or-later；**LGPL-2.1 §6 允许
重标注为 GPL v2+**，与上游 GPL-2.0-or-later 静态链接兼容）到 `third_party/obstack/`，
配方 `exports_sources` 随行、`source()` 摊平进源码树，上游 Makefile 的
`wildcard *.c` 自动把 `obstack.c` 纳入 `objects`；`CPPFLAGS=-I.` 是必需的，
因为引入方式是尖括号而非 `"…"`。

## 解法（可复用步骤）

1. **先分清烧的是哪类路径**：只影响编译/链接 ⇒ make 覆盖即解（M18）；
   程序运行时要用 ⇒ 必须另开覆盖口。
2. **`PREFIX` 留空 + 四路绝对路径分离注入**，绕开 `$(PREFIX)$(SPOOLDIR)` 双拼，
   并让编译宏与 `install` 落点取同一组值。
3. **覆盖口做成环境变量**（`ANACRON_SPOOL`），语义为"缺省仍用编译期宏" ⇒
   本机/CI 各自 `conan create` 零配置可用，跨机复用二进制时才有逃生口。
4. **临时文件改用程序已 chdir 进入、且由本包拥有的可写目录**，
   不要指望环境变量（实测本平台 libc 忽略 `TMPDIR`）。
5. **`getpwuid` 失败分支收窄为环境变量兜底**，不要沿用上游的 `die_e()`。
6. **缺系统头文件 ⇒ 先查制品仓，且检索词必须覆盖别名变体**（本包首版四个精确名
   漏了 `musl-obstack`，把 vendor 误写成唯一出路）；确认有包后仍按包形态取舍 ——
   application 包优先 vendor 免 shared 依赖，**查不到才 vendor 只是兜底而非前提**，
   许可证与来源写进 `notes.md`。
7. **验收必须真跑一次「配置 + 落地 + 时间戳」**：只验 `conan create` 编译通过
   和 `anacron -V`，拦不住"装完一跑就中止"的包。

## 查重结论（四范围 + 引擎，2026-10-06 实测）

| 范围 | 关键词 | 结果 |
|---|---|---|
| `经验文档/适配经验汇总.md` | tempnam / obstack / getpwuid / spool / ANACRON | **0** |
| `knowledge/graph/index.tsv` | tempnam / obstack / spool | **0** |
| `经验文档/经验库/` | tempnam / obstack / spool / ANACRON | **0** |
| `经验文档/B草稿库/` | tempnam / obstack / spool / ANACRON | **0** |
| `knowledge/drafts/` | tempnam / obstack | ⚠ **非 0（W4 P1-1 更正）**：`tempnam` = **4 文件**（本包 2 + `DRAFT-c-ares-lite-1.33.1-harmonyos-autotools-portability.{kv,md}` 2）；`obstack` = **12 文件**（本包 2 + `DRAFT-dwarves-public-header-shim-transitive` / `DRAFT-argp-musl-gap-bridge` / `DRAFT-dejagnu-toolchain-assembly-ohos` / `DRAFT-ohos-musl-strlcat-strlcpy-gap-bridge` / `DRAFT-ohos-configure-probe-self-load-failure-misjudges-version` 各 2） |
| `ohc-run.py engine` 检索 | 本包错误串 | 命中 **E482**（zsh `TMPPREFIX`）——shell 层，与 C 层 `tempnam` 不同机制 |

**已知近邻（`similar_to` 已写明，不占本 PR 知识位）**：

- **M18**（`DRAFT-PKG-VER-suckless-baked-paths-makevar-override`）：`cc` 别名缺失与
  构建期路径烧死，与本包第一条错误**逐字相同**，解法同为 make 变量覆盖 ⇒
  本包不重复申报该层；
- **E108**（`install`/`ginstall`/`Error 127`）、**E174**（`install: No such file`）、
  **M13**（`INSTALL_*` 变量覆盖）：本包同样撞到"平台无 `install(1)`"，
  已被既有条目覆盖；
- **E338**（`getpwuid`/`homedir` 返回 NULL）：同族，但签名是解引用 `SIGSEGV`、
  解法是环境变量注入路径；本包签名是上游 `die_e()` 主动中止；
- **E002**（`/tmp` 只读）：常规解法 `TMPDIR` **实测本包无效**（见上对照表）；
- **★ `knowledge/drafts/` 两条近邻（W4 P1-1 补披露，原表误报 0）**：
  - **`DRAFT-c-ares-lite-1.33.1-harmonyos-autotools-portability.md:65`**「测试可移植性补充：
    `tempnam(NULL)` 与 `$TMPDIR`（OHOS，R15）」—— 其根因「OHOS 上 `tempnam(NULL, prefix)`
    忽略 `$TMPDIR`、回退到只读 `/tmp`」与本包**同一机制**（连「直接设 `$TMPDIR` 对未修改
    入口无效」都逐点一致）⇒ **本条的 tempnam 层不作新知识主张**，只作组合组分；
    差异 = 它触发在上游 gtest 测试的 `TempFile`/`TempNam`（20 用例失败）、解法是打补丁改入口，
    本包触发在守护运行时 `runjob.c`、解法是 `tempnam(已 chdir 进入的自有 spool, 前缀)`。
  - **`DRAFT-dwarves-public-header-shim-transitive`**（`.kv:10` 的 `error_signature` 含
    `fatal error` + `obstack.h file not found`）与本包**首条 obstack 错误同签名**，
    但其解法是 `requires musl-obstack/1.2.3` 垫片（`DRAFT-argp-musl-gap-bridge:26` 同族）；
    本包是 application 形态选 vendor ⇒ **obstack 层同样不作新知识主张**。
  ⇒ 据此**重申 `create`**：本条新知识位只落在**核心层**——运行时 spool 路径烧死 + 上游无覆盖口 +
    `$(PREFIX)$(SPOOLDIR)` 双拼矛盾 + `ANACRON_SPOOL` 覆盖口（W4 已核该层确无近邻），
    tempnam/obstack 两层按 `§6.2`「组合型知识不判重」作为组分随附披露。

⇒ **`B判定 = create`**：本条主张的新知识是**「运行时行为路径烧死 + 上游无覆盖口 ⇒
`PREFIX` 留空四路分离注入 + 新增环境变量覆盖口」**这一层，配合 `tempnam`/`obstack`
两个本平台特有分支，四范围 0 命中。

## 验证证据

```
$ conan create archives/a/anacron/2.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
rc=0
PASS: anacron resolves to <cache>/.../bin/anacron
PASS: version banner: Anacron 2.3
PASS: anacrontab parsed and job scheduled
PASS: job executed via fork/exec + /bin/sh -c
PASS: spool timestamp created (.../spool/smokejob)
PASS: ANACRON_SPOOL override reaches chdir()
PASS: -u updates the timestamp without running the job
ALL TESTS PASSED
```

反向验证（覆盖口确实生效）：`ANACRON_SPOOL=<不存在目录>` ⇒ 非零退出 +
逐字 `Can't chdir`，证明该变量真的驱动了 `chdir()`，而不是装饰性的。
