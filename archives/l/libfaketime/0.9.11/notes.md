# libfaketime 0.9.11 适配笔记

## 编译环境
- 构建系统: makefile（上游无 configure / 无 automake；顶层 Makefile 只有 `all` / `test` / `install`）
- 编译日期: 2026-09-25
- 编译器: clang 15（`/data/service/hnp/bin/clang`，由 `ci/conan/profiles/ohos-aarch64` 的 `tools.build:compiler_executables:c` 提供）
- 平台: OHOS aarch64（HarmonyOS PC 真机，arch=armv8 / os.version=6.0）
- 状态: built（真机 `conan create` 通过，尚未由 CI upload）

## 编译步骤

```sh
# profile 必须是仓库权威那份，conan-init 生成的 default profile 缺 os.version，
# 会在 Computing necessary packages 阶段报 'settings.os.version' value not defined
conan create archives/l/libfaketime/0.9.11/conanfile.py \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方内部实际执行的命令（`basic_layout(src_folder="src")`）：

```sh
make -j1 CC=/data/service/hnp/bin/clang PREFIX=<package_folder> \
     LIBDIRNAME=/lib/faketime VERSION_SCRIPT=libfaketime.map.ohos \
     FAKETIME_COMPILE_CFLAGS="-Wno-error=unused-command-line-argument -Wno-self-assign \
       -Wno-error=unused-but-set-variable -DFAKE_RANDOM -DFAKE_PID"            # 编译 src/ + bin/faketime
PATH=/data/service/hnp/bin:$PATH make -j1 <同上变量> test                       # timetest + testframe 套件 + test.sh
PATH=/data/service/hnp/bin:$PATH make -j1 <同上变量> snippets -C test           # 6 expectation + 6 snippet
make <同上变量> DESTDIR="" install                                             # 顶层 install：src + man + doc
```

`make -j1`（而非 `-j2`）是必要的：HMDFS 上 make 的 jobserver 需要 `mkfifo`，本机
`mkfifo` 报 `Operation not permitted`，任何 `-jN>1` 都直接失败（见下表 #3）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接 `libfaketime.so.1` 报 `ld.lld: error: symbol timer_gettime@GLIBC_2.2 has undefined version GLIBC_2.2`（共 8 个符号） | 上游把 interposer 绑到 glibc 符号版本节点：`__asm__(".symver X, name@GLIBC_2.x")` + `src/libfaketime.map` 里的 `GLIBC_2.x { }` 段。musl/OHOS 无符号版本机制，`libc.so` 里不存在 `GLIBC_2.x` 版本定义 | 补丁 0002（`src/libfaketime.c`）：把 `.symver` 整块收进 `#if defined __GLIBC__`，`#else` 分支用 `__attribute__((alias))` 把当前 ABI 变体（`timer_settime_233` / `timer_gettime_233` / `pthread_cond_*_232`）以**未版本化的公开名**导出 |
| 2 | 试过去掉 `@`，写 `.symver timer_gettime_233, timer_gettime` → `<inline asm>:1:21: error: expected a '@' in the name` | OHOS 的 clang 内联汇编前端（IntegratedAsm/AArch64）要求 `.symver` 第二个参数必须带 `@`，不接受"无版本别名"这种 glibc 惯用写法 | 放弃 `.symver` 路线，改用 `__attribute__((alias))`（纯 ELF 符号别名，不经过版本语法） |
| 3 | `make: jobserver: mkfifo /tmp/MakefXXXX: Operation not permitted` | HMDFS 不允许创建 FIFO，GNU make 的 jobserver 通道建不出来 | 显式 `make -j1`，并 `unset MAKEFLAGS`（conan 的 `tools.build:jobs=2` 会经 MAKEFLAGS 注入） |
| 4 | `libmallocintercept.c:79: error: variable 'ptr2' set but not used [-Werror,-Wunused-but-set-variable]`；`timetest.c:71: error: implicitly disabling a copy ... [-Werror,-Wself-assign]`；以及 `-Werror` 与 hnp clang 包装器注入的 `-Wl,--code-sign` / `-fuse-ld=lld` 冲突 | 上游 `CFLAGS = -Wall -Werror -Wextra` 只针对 gcc；clang 多出的两个诊断 + 包装器注入的命令行参数触发 `-Wunused-command-line-argument` | 通过 `FAKETIME_COMPILE_CFLAGS` 追加 `-Wno-error=unused-command-line-argument -Wno-self-assign -Wno-error=unused-but-set-variable`（不改上游 `-Werror`，只关 clang 特有诊断） |
| 5 | `test/testframe.sh: No such file or directory` | 脚本 shebang 是 `#!/bin/bash`，**OHOS 上不存在 `/bin/bash`**（bash 由 HNP 装在 `/data/service/hnp/bin/bash`） | 补丁 0005/0006：`test/testframe.sh`、`test/test_variable_data.sh` 改 `#!/usr/bin/env bash`；`test/functests/test_exclude_mono.sh` 里硬编码的 `/bin/bash -c` 改 `bash -c` |
| 6 | `# PLATFORM=unsupported platform, uname="HarmonyOS" ... unknown platform! quitting` | `test/functests/common.inc` 的 `platform()` 只 case `Linux`/Darwin/SunOS | 补丁 0003（`test/functests/common.inc`）：`*Linux*` → `*Linux*|*HarmonyOS*|*OHOS*` 归为 `linuxlike` |
| 7 | `Time::HiRes::clock_gettime(): unimplemented in this platform` → `test_exclude_mono.sh` 1 个用例失败 | 用户态 `$HOME/usr/local/bin/perl` 是自己编译的，`Time::HiRes::clock_gettime` 在该平台未实现；HNP 的 `/data/service/hnp/bin/perl` 实现了 | 跑测试时前置 `/data/service/hnp/bin` 到 `PATH`（配方 `_with_hnp_perl()`），只影响测试阶段，不改 profile 的 PATH 语义 |
| 8 | snippets 阶段 `run_getpid` / `run_getrandom` / `run_getentropy` 断言不成立 | `getpid`/`getrandom`/`getentropy` 的拦截在 `#ifdef FAKE_PID` / `#ifdef FAKE_RANDOM` 后面，上游默认不开这两个 opt-in 特性，而 0.9.11 的 snippet 测试套件已经在驱动它们 | `FAKETIME_COMPILE_CFLAGS` 加 `-DFAKE_RANDOM -DFAKE_PID`（同时使消费者测试能覆盖这两条路径） |
| 9 | `-DINTERCEPT_SYSCALL` 未开启 | 上游 `test/Makefile` 在 CFLAGS 不含该宏时把 `syscall*` snippet 与 `confirm_variadic_promotion` 从 `ALL_TESTS` 中 `filter-out` | 保持上游默认口径（不开启），6 个门控测试逐项登记为"未执行 + 原因"，不静默并入通过数 |
| 10 | 安装后的 `bin/faketime` 权限 0660，execve 报 `Permission denied` | E543：HMDFS 默认文件模式 660（仓库侧对应 `knowledge/operations/packaging.md`「签名后权限重置为 660」条目） | `package()` 内 `os.chmod(bin/faketime, 0o755)` |
| 11 | 产物无法加载（未签名 ELF 被拒） | HarmonyOS XPM 要求 ELF 自签 | `package()` 内 `env -u LD_LIBRARY_PATH` 调 hnp `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`（三个产物：`bin/faketime`、`libfaketime.so.1`、`libfaketimeMT.so.1`） |
| 12 | 测试日志刷屏 `job-working-directory: error retrieving current directory: getcwd: cannot access parent directories` | E386 家族：profile `[buildenv]` 把 `SHELL`/`CONFIG_SHELL` 钉在 hnp bash，而它在 HMDFS 构建目录下 `getcwd()` 必挂 | 本次为**纯噪音**：所有用例仍按预期产出 `- ok` / `summary: N succeeded, 0 failed`，两条 make 目标退出码 0，因此不引入 `env -u CONFIG_SHELL` 变通（避免偏离 CI profile 口径），只在笔记与正文的"已知限制"中登记。**2026-09-25 CI 复算修正：这条噪音不是纯噪音**——它是该构建目录下 `..` 无法解析的直接信号，正是问题 #16 在 CI worker 上暴露的根因 |

| 13 | `faketime '-15d' <prog>` 报 `date: bad date -15d` / `Error: Timestamp to fake not recognized` | `src/faketime.c` 的 CLI 包装器不自己解析时间串，而是 `execlp("date", "date", "-d", <spec>, "+%s")` 交给外部 `date`。OHOS 系统 `date` 是 **toybox 0.8.12**，`-d` 只支持绝对时间（`2000-01-01 00:00:00`、`@<epoch>`、ISO8601），相对表达式一律 `bad date`；设备上另有 GNU coreutils 9.10（`~/usr/local/bin/date`），但它对 `-15d` / `15 days ago` 同样报 `invalid date`，因此不是"换个 date 就行"的问题 | **不改上游行为**，改为按平台能力申报限制：`test_package` 的场景 1 用绝对时间串（由 `time.localtime` 反推，避免依赖具体时区），`bin/faketime` 的相对偏移用法在"已知限制"中登记；LD_PRELOAD + `FAKETIME` 路径不受影响（libfaketime 自己解析，`-15d`/`+10d x1`/`@绝对` 全部实测可用） |
| 14 | 安装后的 `bin/faketime` 权限位显示 `-rwxr-x---` | HMDFS 对 owner 之外的位显示不可信（AGENTS §4 写权限以 `touch` 探针为准）；`os.chmod(0o755)` 已执行，owner 的 rwx 生效、execve 实测通过 | 不做额外处理，仅在此登记，避免后人误判 chmod 失败 |
| 15 | 消费者测试初版用 `FAKERANDOM_SEED=20260925/20260926`，断言"换种子必须得到不同字节流"失败（两串都是 32 个 `0`） | `fakerandom_msws()` 逐次调用后第 i 个输出字节等于 `(i*seed) >> 32` 的低 8 位（平方项在 mod 2^64 下退化为 0）。⇒ **一次 16 字节读要出现非零字节必须 `16*seed >= 2^32`，即 seed >= 2^28 约 2.68e8**；`1`/`2`/`20260925`/`20260926` 都低于该阈值（实测四条流全零），`1234567890` 恰从第 4 字节起非零（`4*1234567890>>32 == 1`，与实测 `00000001911c4b5b...` 逐字节吻合）。上游 `test/snippets/getrandom.variable` 用 64 位种子 `0xDEADBEEFDEADBEEF`，正避开该退化区 | 不是 OHOS 特有缺陷，属上游 PRNG 的取值口径；消费者测试改用与上游同规格的 64 位十六进制种子（`0x0123456789ABCDEF` vs `0xDEADBEEFDEADBEEF`，实测流 `67873487188ea54f...` / `ff00ff05e897c6fa...`），断言口径为"同种子跨进程可复现 + 换种子必须不同"，不引入"非零"这类对 PRNG 质量的主观要求；已在 `misc_probe.c` 注释与 `test_package/MANIFEST.yml` 登记 |
| 16 | **CI worker 上 `test_walkone.sh` 31 个用例全失败**（`out=1790336398 (secs since Epoch) expected=1 - bad` … 一直到 `expected=1073741824`），而同一份代码在真机 4 套件 34 个原子用例全绿 | 上游测试驱动用**相对路径**预加载：`test/functests/common.inc:42` 的 `FTPL="${FAKETIME_TESTLIB:-../src/libfaketime.so.1}"`（`test.sh` / `test_variable_data.sh` / `test_constructors.sh` / `randomtest.sh` 同规格）。**musl 的加载器对"打不开的 LD_PRELOAD 条目"是静默忽略**（不打印任何诊断、子进程退出码仍为 0），而 CI worker 的构建目录恰好处在 `..` 解析不了的环境里（日志同一位置报 `getcwd: cannot access parent directories: Not supported`）⇒ 预加载根本没发生、`date +%s` 打印真实时间。另外 3 个套件在**完全没加载 libfaketime** 的情况下也照样通过（`test_null` 只断言真实时间非 0、`test_true` 不测时间、`test_exclude_mono` 只跑 `dont_fake_mono` 分支即"不伪造时应当不同"），所以只有真正要求"时间被改成 2^i"的 walkone 暴露 | 用上游自带的开关 `FAKETIME_TESTLIB` 把预加载路径换成**绝对路径**：配方新增 `_preload_env_var()`，在 `make test` 与 `make -C test snippets` 两条目标前注入 `FAKETIME_TESTLIB="<source_folder>/src/libfaketime.so.1"`。**不改任何断言、不减任何用例、不加新补丁文件**，数字账本（34/9/12）保持不变；顺带消除了"相对路径打不开 → 静默假通过"这一类风险。**本地反证 + 正证**（`~/tmp/uc2/TGFAT-1/`）：`FAKETIME_TESTLIB=/nope/libfaketime.so.1 ./testframe.sh functests` 精确复现 CI 症状（`walkone summary: 0 succeeded, 31 failed`，且无任何预加载报错），设为绝对路径后 `31 succeeded, 0 failed`、`Test Suites summary: 4 succeeded, 0 failed`。**⚠️ 本行的因果推断已被第二轮 CI 证伪**：绝对路径确实下发到了 worker（build #61128 日志的 `RUN:` 行可见），walkone 仍 `0 succeeded, 31 failed` ⇒ 预加载路径不是真因，见 #17 |
| 17 | **第二轮 CI（build #61128，head `9f70159d4`）`test_walkone.sh` 仍 0/31**，症状与 #16 逐字相同（`out=<真实 epoch> expected=2^i - bad`、无任何预加载报错、另外 3 套件照旧通过），而 `FAKETIME_TESTLIB` 绝对路径已生效、同一份配方在本机 31/31 | **真因在 `date` 这个被预加载的目标进程，不在库路径**：worker 的环境块显示它的 `PATH` 以 `/data/app/bin`（`HNP_PRIVATE_HOME=/data/app`）开头，而本机 `ls /data/app/bin` 直接 `No such file or directory` —— 两台机上 `date` 解析到的根本不是同一个二进制。上游驱动只写裸命令 `date`（`test/functests/common.inc` 的 `linuxlike_fakecmd` → `FAKETIME="$t" date +%s`），`FAKETIME_TESTLIB` 能钉住库、钉不住被注入的目标；目标若是静态链接（或不属于本机同一 libc），musl 加载器依旧静默跳过。本机 `/usr/bin/date -> ../../bin/toybox`（动态）实测可注入：`LD_PRELOAD=<abs> FAKETIME=12345 date +%s` → `12345` | 两层改动，全部在环境层、不碰任何被测代码与断言：① `_with_hnp_perl()` 的 PATH 由 `/data/service/hnp/bin:$PATH` 改为 `/data/service/hnp/bin:/usr/bin:/bin:$PATH`，把系统目录钉在 worker 的 HNP 私有 bin 之前，使测试跑在实测可注入的 toybox `date` 上（HNP 目录仍在前，perl/bash/make 口径不变）；② 新增 `_assert_preload_effective()`：跑套件前先用同一绝对路径做一次 `FAKETIME=1 → date +%s == 1` 探针，不成立即 `exit 1` 并打印 `date=$(command -v date)` 与实测值——把「静默假通过」变成带目标路径的显式失败，避免再靠 31 条断言反推环境。**本地证据**（`~/tmp/uc2/TGFAT-1/`）：`create14.log` 20:44 rc=0（`walkone 31 succeeded` + `Test Suites summary: 4 succeeded, 0 failed`）；改探针为 POSIX `command -v`（`/system/bin/sh` 的 `type` 无 `-P`，会打 `whence: -P: unknown option`）后 `create15.log` 20:47:53 rc=0、无 shell 噪音、31/31；反证 `LD_PRELOAD=<不存在的 .so>` → `out=1790340383`（真实时间）且退出码 0，正证同一命令换成本轮产物 → `out=1`；`finish6.log` 20:53 阻塞门禁（G1/G2/G3、conan-verify、W3 本地 CI 模拟、W2）全绿 **⚠️ 本行"worker 上 `date` 解析到另一个二进制"的归因已被第三轮 CI（build #61148，head `4e1362c1a`）证伪，见 #18** |

| 18 | **第三轮 CI（build #61148，head `4e1362c1a`）探针直接给出 `libfaketime probe failed: date=alias date=date out=1790341356 expected=1`** —— PATH 已按 #17 钉成 `/data/service/hnp/bin:/usr/bin:/bin:$PATH`，worker 上仍然伪造不了 | #17 的归因（"worker 的 `date` 是另一个二进制"）**被这一行日志证伪**：① `command -v date` 在 worker 上回 `alias date=date`，是自引用别名，展开后仍走 PATH 查找，不构成重定向；② 本机同一个 `/system/bin/sh`、同一份 clang 产物实测 `LD_PRELOAD=<abs> FAKETIME=1 FAKETIME_FMT=%s /usr/bin/date +%s` → `1`，"目标不可注入"不成立；③ worker 上加载器一声不吭 ⇒ 落点只剩"**该 worker 拒绝映射这个 .so**"。而本配方 `package()` 早就对交付产物做了两道 OHOS 处理——E543 的 `chmod 0755`（HMDFS 默认位让 `execve()`/加载器拒绝）与 XPM 的 `binary-sign-tool` 自签——**唯独 `build()` 里被测试套件直接预加载的构建树 .so 两道都没做过**（本机产物实测 `-rwxr-x---` 且未签名；本机策略宽松能加载，worker 不保证） | `_assert_preload_effective()` 从"一次性断言"升级为**分级修复 + 一次性取证**：①按现状试 → ②对 `libfaketime.so.1`/`libfaketimeMT.so.1`/`faketime` 做 `chmod 0755` 再试 → ③`llvm-objcopy --remove-section .codesign` + `binary-sign-tool -selfSign 1`（与 `package()` 同一套命令、同一 `env -u LD_LIBRARY_PATH` 口径）再试；任一级生效即打印 `ok after <stage>` 并放行套件（套件预加载的就是这个 .so，修复对它同样有效），三级都失败才 dump 取证矩阵（uid / shell exe / `command -v date` / PATH / ld-musl / .so 模式与 `codesign` 段计数 / **加载器 stderr 原话** / 六个 `date` 候选各自的 ELF Type 与伪造结果）。**本机证据**：探针第 ① 级即 `ok (as built)`（本机不需要修复），`create17.log` 21:30:39 rc=0、`walkone 31 succeeded`、`Test Suites summary: 4 succeeded, 0 failed`、MEMCAP peak=159MB；把 `SRC` 指向不存在目录跑反证，矩阵在真机完整输出并 `exit 1`，证明取证分支可用。断言与用例数一字未改。 |

| 19 | **第四轮 CI（build #61177，head `1f5c0526d`）取证矩阵落地：#18 的分级修复三级全部无效** —— `as built -> NOT faked` / `after chmod 0755 -> NOT faked` / `after self-sign -> NOT faked`（`binary-sign-tool` 两次都回 `write code sign data success`，签名本身成功）。矩阵接着给出 `loader stderr : （空）` 与 `is it mapped at all? : Fri Sep 25 21:53:39 CST 2026`——故意不给 `FAKETIME_FMT`，被真正加载的 libfaketime 必然报 `failed to parse FAKETIME timestamp`，这里一声不吭 ⇒ **该 .so 根本没进进程地址空间** | 两条归因（文件模式、缺签名）在构建树这一层**双双证伪**，矩阵顺手证伪了 #17 残留的最后一分怀疑：worker 上 `/data/app/bin` **同样不存在**（`ls: /data/app/bin: No such file or directory`），六个候选里 `/usr/bin/date`、`/bin/date`、`/system/bin/date` 都是 `type= DYN (Position-Independent Executable file)`、都打印真实时间 `1790344419`，加载器同为 `/lib/ld-musl-aarch64.so.1`——两侧根本是同一类目标二进制。剩下的唯一未测变量是**对象本身在该 worker 上下文里是否被接受**（本机 .so 属主即本进程 uid；worker 上 `ls -l` 回 `20001006` 而 `id` 回 `bad uid 20020101`，HMDFS uid 虚拟化、权限位显示本就不可信），以及它所在挂载点 | `_assert_preload_effective()` 从“分级修复”再升级为**分级选择并把可用对象交给套件**：`r1 现状` → `r2 chmod 0755` → `r3 由本进程新建一份副本（属主与位由自己决定）` → `r4 该副本去 .codesign + 自签` → `r5 副本放 $TMPDIR`（可能是另一个挂载点）`；任一级可用即写入 `.lft-preload-target`，Python 侧读回后由 `_preload_env_var(lib)` 把**这一级选出的对象**发给套件，五级全不可用则在 dump 之后 `raise`，绝不静默放行。矩阵补 `TMPDIR` 及其 `ls -ld`、`/proc/self/mounts` 的 storage 行、`lib NEEDED`。脚本由单行分号串改为**每句一行**（三种 shell `sh -n` 均过）。**本机证据**：`create18.log` 22:08:27 rc=0，`r1 as built -> VIABLE <abs>/b/src/src/libfaketime.so.1`、`walkone 31 succeeded`、`Test Suites summary: 4 succeeded, 0 failed`；新增的 wrapper control 行在真机打印 `date: bad date 1`（问题 #13 同一 toybox `-d` 限制的第三次独立复现，非新问题）；`finish9.log` 22:12:37 G1/G2/G3、conan-verify、W3 本地 CI 模拟全绿（rc=2 仍是 #11 登记的 step5b/step8 框架缺陷）。**断言与用例数一字未改**（62 静态 / 55 注册 / 55 执行 / 7 未执行 / 12 场景消费者） |
| 20 | **第五轮 CI（build #61220，head `fd381de2d`，worker `OpenHarmonyPCDeveloper-CI-028`）分级选择器五级全部不通过：该 worker 的加载器不接受任何来自用户存储的 `LD_PRELOAD` 对象** | 矩阵原话：`r1 as built -> not faked` → `r2 ... after chmod -> not faked`（而且 `chmod '.../src/faketime' to 0755: Permission denied`——worker 上连 chmod 都不被允许，与本机 #18/#19 的行为不同） → `r3 owned copy -> not faked`（本进程 `cp` 新建的对象，`-rwxr-x--- 1 20001006 file_manager`） → `r4 owned copy after self-sign -> not faked`（`binary-sign-tool` 明确回 `write code sign data success`） → `r5 tmpdir copy -> not faked`。存活判据给出机制结论：故意喂不可解析的 `FAKETIME=1` 且**不给** `FAKETIME_FMT`，`date` 输出正常日期 `Fri Sep 25 22:24:10 CST 2026` 而不是 libfaketime 的 `failed to parse FAKETIME timestamp` 抱怨 ⇒ **.so 从未被映射进进程**（与`loader stderr` 为空一致）。挂载证据：`/storage/hmdfs`、`/storage/External` 均为 `tmpfs rw,nosuid,...,hmmac=use_task,seclabel`；而 r5 期望的"另一块挂载"实际没换到——`$TMPDIR` 被 conan 覆写成 `/storage/Users/currentUser/.cache/tmp`（CI 环境原值是 `/data/storage/el2/base/cache`），所以"非 hmdfs 挂载"这一档**实测未覆盖**，是本次唯一未消除的自由变量 | 对照：同一份配方在本机 `create18.log`（22:08:27 rc=0）第一级即 `r1 as built -> VIABLE`、`test_walkone.sh summary: 31 succeeded, 0 failed`。**定性：CI worker 侧加载器/策略差异，不是配方缺陷，本机不可复现、也不由本机修。**配方维持"预检不过即硬失败、并把机制打出来"（宁可红也不静默假通过）；证据矩阵已写进 PR 正文。按 R43 五连败止损，**不再自行发起第六轮**，上报用户决定是否向平台求证 worker 的 `LD_PRELOAD` 策略 |
| 21 | **② 实验获委托方授权执行：更正 #20 的定性——这不是未知策略差异，而是仓库既有知识已被命中，且我方五级矩阵变动的是错的变量** | 自查证据链：①`knowledge/doc/E502.md` 标题即 `OHOS CI workers refuse dlopen and LD_PRELOAD of every user-directory shared object regardless of ELF signature while exec-time NEEDED loading still works`（根因段写明：进程启动后再映射的用户目录对象一律拒、新自签与 release 签名都一样；同一批对象作 exec 期 `DT_NEEDED` 则正常加载，实证 isl C 测试对 build-time 签名的 `libgmp.so.10` 通过，build #33895）；②`knowledge/doc/E465.md` 给出唯一被接受的映射路径=进程启动期 DT_NEEDED 链（自建 launcher）；③**已合入的 `archives/d/datefudge/1.27` 是同一堵墙的直证先例**——其 `notes.md` 第 35 行「OHOS worker 的系统 Perl 执行 `localtime(time)` 时不会被该预加载库的 `time()` 符号拦截」，被接受的修法是把**注入目标**换成仓库已发布的 conan 二进制（`build_requirements()` 里 `test_requires("perl/5.42.2")` + `make test PERL="<绝对 conan perl>"`，取不到即 raise 防 shell 静默回退），并 `requires("coreutils/9.10", headers=False, libs=False, run=True)` 拿 GNU `date`，仅在 `_can_run_ohos_binaries()` 成立时 `prepend_path("PATH", coreutils_bin)` ⇒ **decisive variable 是被注入程序的来源，不是预加载对象的位置/签名**（datefudge 的 `.so` 仍在用户目录且生效）。我方 #20 把现象定性为「CI worker 侧加载器/策略差异，本机不可复现、不由本机修」不完整，以本行为准。配方改动（同一次提交内）：`_assert_preload_effective()` → `_select_preload_pair()`，**对象档位 × 注入目标**二维矩阵（对象侧仍为 r1 原件→r2 chmod→r3 本进程新建副本→r4 副本自签→r5 `$TMPDIR` 副本；目标侧 = worker 系统 `date` 与 conan `coreutils` 的 `date`），命中即把**这一对**交给上游套件（`FAKETIME_TESTLIB=<lib>`，并在 `_with_hnp_perl()` 的 PATH 里把该目标所在 `bin` 前置在 `/data/service/hnp/bin:/usr/bin:/bin` 之前——不前置则 `/usr/bin/date`(toybox) 会遮蔽选中目标，判定就白做）；**任一对都不通过仍然 raise**，预检与断言口径一律未放宽。`test_requires("coreutils/9.10")` 只在 OHOS 声明且是 test 级（不进 requirements、不改 package_id）。本机验证（`~/tmp/uc2/TGFAT-1/create19.log`，2026-09-26 rc=0）：第一级第一目标即 `r1 as built / system date -> VIABLE ... prepend=`，`test_walkone.sh summary: 31 succeeded, 0 failed`、`Test Suites summary: 4 succeeded, 0 failed`——**与 create18 完全同口径、测试数字未变**，即本次改动对本机行为零影响（新档位只在 worker 上才会被走到） | 结论与风险：本机证明不了 worker 的行为（E502 明写「interactive device 更宽松，本地成功不可迁移」）。本行改动的最终判定只能来自第六轮 CI；若届时矩阵显示 conan 目标被 fake，则上游 55 个已注册用例在 CI 上真实执行；**但不要据此以为「已知限制 #1」被解除**——同批探针实测：`/usr/bin/date` 是 toybox 0.8.12，`-d '-15d'` 与 `-d '15 days ago'` 都报 `bad date`；conan `coreutils/9.10` 的 `date`（GNU coreutils 9.10）对 `-d '15 days ago'` 回 `1789113869`、对 `-d '-15d'` 仍报 `invalid date`（前导 `-` 被当成选项）。即相对偏移不可用的根因是 `faketime` 交给外部 `date -d` 的串本身不被两解接受，换目标不解决它，`test_package` 仍按绝对时间串场景交付；若仍全否，则与 ① 的平台求证结论合并归档，按 ③ 释放任务，不做假绿交付 |
## 源码修改

补丁按"每个已存在源文件一份"登记（本仓 `refresh-patch --auto` 的输出形态，见下"补丁布局"一节）：

### `patches/0001-src-Makefile.patch`（strip 1）

把写死的 `--version-script=libfaketime.map` 参数化为 `$(VERSION_SCRIPT)`，默认值仍是上游那份脚本，因此 Linux/glibc 构建行为零影响；配方侧传 `VERSION_SCRIPT=libfaketime.map.ohos`。

### `patches/0002-src-libfaketime.c.patch`（strip 1）

两处 `.symver` 块（POSIX 定时器组、pthread_cond 组）分别包进 `#if defined __GLIBC__ / #else / #endif`，`#else` 用 `__extension__ extern __typeof__ (...) name __attribute__((alias("..._233")))` 导出公开名。

> **与仓库既有 0.9.10 归档的差异（这是本 PR 的实质增量）**：`archives/l/libfaketime/0.9.10/patches/0002-disable-glibc-symver.patch` 的做法是**整块删掉** `.symver` 声明和 version script。删掉之后 `timer_settime_233` / `timer_gettime_233` / `pthread_cond_timedwait_225` / `pthread_cond_timedwait_232` / `pthread_cond_init_232` 这些实现函数**没有任何公开名指向它们**，等于在 OHOS 上悄悄丢掉了 `timer_settime()`/`timer_gettime()`/`pthread_cond_timedwait()` 的拦截能力（且这些内部名反而会被导出污染 ABI）。本补丁保留全部 5 个拦截点，并让它们被 `local` 正确隐藏。两者都可用 `nm -D` 与 `test_package/abi_probe.c` 复核。

### 配方生成 `src/libfaketime.map.ohos`（不在补丁里）

匿名（无版本节点名）的 local-only 链接脚本，只把 5 个 `_22/_232/_233` 实现符号设为 `local`，其余全部公开导出。它由 `build()` 用 `conan.tools.files.save()` 写到 `src/` 下（`make` 在 `src/` 里链接，相对路径即命中）。**不放补丁**的原因见"注意事项 #8"：`refresh-patch --auto` 只为已存在的文件重生成补丁，新增文件段会被丢掉，那样配方会指向一个不存在的补丁。

### `patches/0003`～`patches/0006`：上游测试入口（strip 1）

`test/functests/common.inc`（uname 识别）、`test/functests/test_exclude_mono.sh`（去 `/bin/bash`）、`test/test_variable_data.sh` 与 `test/testframe.sh`（shebang 改 `env bash`）。全部只作用于测试驱动，不触碰被测代码。

## 依赖版本

无第三方依赖（只依赖 libc / libpthread / librt，musl 内置 resolver，故 `LDLIBS` 不额外挂 `-lresolv` 之类）。`tool_requires` 亦未声明——`make` / `clang` 全部来自 profile。

## 测试口径（五维账本，四处同源）

| 维度 | 数量 | 来源 |
|---|---|---|
| `N_static` 上游静态声明 | **62** | testframe 4 套件 34 个原子用例（1+1+1+31）+ `test.sh` 9 个场景 + snippets 12（6 expectation + 6 snippet）+ `-DINTERCEPT_SYSCALL` 门控 6 + 上游故意失败样例 `dont_test_false.sh` 1 |
| `N_registered` 构建系统注册可执行 | **55** | 上游默认 CFLAGS 下 `make test` + `make -C test snippets` 实际注册并运行的部分 |
| `N_executed` 真机实际执行 | **55** | 两条 make 目标退出码均为 0（见下"验证结果"） |
| 未执行 / 跳过 | **7** | 6 个受 `-DINTERCEPT_SYSCALL` 门控（构建系统根本不注册）+ 1 个上游 `dont_` 前缀故意失败样例；逐项原因见 `test_package/MANIFEST.yml` |
| `N_consumer` 新增消费者测试 | **12 个场景 / 4 个程序 / 54 条断言** | `test_package/{clock_probe,cond_probe,abi_probe,misc_probe}.c` |
| 适配后合计 | **67 ≥ 62** | 55 + 12 |

`timer_getoverrun(timerid1) FAILED, must be 3 but got: 4` 的定性：它在**全部 9 个场景**复现，包括"LD_PRELOAD 但不设 FAKETIME"的基线场景，因此与时间伪造无关，是本机 POSIX 定时器 overrun 计数在调度抖动下的不稳定；上游 `timetest.c` 对该项只打印、不设置退出码，`make test` 仍为 0。本 PR 未修改该断言，也未把它并入通过数。

## 验证结果

```console
$ conan create archives/l/libfaketime/0.9.11/conanfile.py \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# ……（完整日志：~/tmp/uc2/TGFAT-1/create17.log，2026-09-25 21:30:39 退出码 0（PATH 钉定那一轮：create16.log 21:19:54 / create15.log 20:47:53；再前：create14.log 20:44）；本轮把预加载自检升级为分级修复 + 取证矩阵（见问题 #18），
#      这是"6 个 per-file 补丁 + version script 由 build() 生成"这一终态布局下，
#      从干净源码树重新导出 → 打补丁 → 构建 → 上游全量测试 → test_package 全跑一遍的完整验证）
# Test Suites summary: 4 succeeded, 0 failed      <- testframe functests 34 个原子用例
# Testing finished.                               <- test.sh 9 个场景
# make -C test snippets                           <- 6 + 6
libfaketime/0.9.11: Export bin/faketime 等 3 个产物
libfaketime/0.9.11 (test package): Running test()  <- 12 个消费者场景（14 条 RUN 记录，含 cmake configure/build）
#   clock_probe: OK x4 + 反向对照如期失败 1 次；cond_probe: OK（等待 1002ms）
#   abi_probe: OK（11 公开符号归属 + 8 内部符号隐藏 + 5 处调用方绑定）
#   getpid() = 424242；FAKERANDOM_SEED 三元组：同种子两流相等、换种子不等、无种子回落真实熵

$ python3 scripts/ohc-run.py finish libfaketime 0.9.11 built
# ……（完整日志：~/tmp/uc2/TGFAT-1/finish8.log，2026-09-25 21:36:31；MEMCAP peak=235MB；同一份布局下的幂等重跑：step1 重生成补丁后 G1/G2/G3、conan-verify、W3 仍然全绿）
# G1 配方完整性 PASS / G2 conan create PASS / G3 系统同名库隔离 PASS / G4 产物完整性
# ✅ 配方验证通过: libfaketime 0.9.11        <- conan-verify（框架提示"可标记 published"，
#                                              本机不采纳：CI 未 upload，状态保持 built）
# ✅ W3 本地 CI 模拟通过（reports/w3-local-ci.log）  [阻塞门禁]
# ✅ W2 仅含配方变更 (20 文件)，无框架文件
# ✅ knowledge gap: manifest.yaml knowledge_count=1 unreferenced=0
# ⚠️ 框架侧非阻塞残留（本 PR 不改框架，见注意事项 #11）：
#    G0 对纯 Makefile 项目报 configure exit 127；
#    step8 gen_summary 抛 'str' object has no attribute 'append'（SUMMARY.md 不手写）；
#    step10 submit 就绪预检要求 reports/test-report.md、packaging/、.staging-verified
#    三个本地流程产物（按 §9 不入 PR），故 finish 退出码 2；
#    阻塞门禁（G1/G2/G3、conan-verify、W3、W2、knowledge gap）全部通过
```

产物清单（`package_folder`）：

| 文件 | 说明 |
|------|------|
| `bin/faketime` | 命令行包装器，编译期烤入 `PREFIX + LIBDIRNAME` 定位 `.so` |
| `lib/faketime/libfaketime.so.1` | 单线程版 LD_PRELOAD 载荷 |
| `lib/faketime/libfaketimeMT.so.1` | 多线程版 |
| `share/man/man1/faketime.1.gz` | 上游 man（顶层 `install` 顺带装 doc） |

## 注意事项

1. **profile 必须用仓库那份** `ci/conan/profiles/ohos-aarch64`。用 `conan profile list` 里的 `default`（`conan-init` 生成）会报 `'settings.os.version' value not defined`。
2. **`make` 一律 `-j1`**，并且在直接调 make 前 `unset MAKEFLAGS`；`-j2` 在 HMDFS 上死于 jobserver `mkfifo`。
3. **`bin/faketime` 与 `PREFIX` 强耦合**：`build()` 与 `package()` 必须传同一个 `PREFIX=<package_folder>`，否则包装器会去找不存在的绝对路径（该路径在编译期以字符串常量写入）。
4. **不得照抄 0.9.10 的"删 .symver"做法**：那会静默丢掉 5 个拦截点。判断拦截是否真的生效用 `test_package/cond_probe.c`（伪造钟上必须真等 ≥800ms）与 `abi_probe.c`（符号归属必须落在 libfaketime.so.1）。
5. `FAKE_RANDOM` / `FAKE_PID` 是上游 opt-in；关掉它们上游 snippets 会失败，本配方默认开启并在 `notes` 与 PR 正文登记。
6. 未执行项（6 个 `INTERCEPT_SYSCALL` 门控 + 1 个故意失败样例）在 CI 上同样不会执行，属于上游构建系统的注册口径，不是本适配引入。
7. 内存画像：整条 `conan create`（含上游全量测试与 test_package）实测峰值 RSS **208–291 MB**（`~/tmp/uc2/TGFAT-1/create12.log` 末行 `MEMCAP[run] peak=208MB budget=1500MB rc=0 用时59.0s`；`finish3.log` 末行 `peak=291MB`；PATH 钉定那一轮 `create14.log` 末行 `peak=211MB`、`create15.log` 末行 `peak=163MB`、`finish5.log` 末行 `peak=175MB`、`finish6.log` 末行 `peak=313MB`）；`test_package` 自身探针是 O(1) 计时程序（峰值主要是 conan + cmake + 上游 date 子进程的常驻量）；预算 1500MB 远超实际需要，`max_rss_mb: 256` 为安全裕度。
8. **补丁布局必须与框架的 `refresh-patch --auto` 输出同形（每个已存在源文件一份）**：本 PR 一度把改动打成 2 个多文件命名补丁，`finish` 第一步就把它们重拆成 6 个 per-file 补丁并**丢掉新增文件 `src/libfaketime.map.ohos` 的 `--- /dev/null` 段**，于是 `conandata.yml` 指向的补丁名不存在、`export_sources()` 直接 `Patch file does not exist` 失败。终态采取框架口径：`conandata.yml` 登记 6 个 per-file 补丁，version script 改由 `build()` 生成。改完后 `conan create` 与 `finish` 都能幂等重跑。
9. **`build_and_test.sh` 的镜像回退会改写活文件 `conandata.yml`**：它在 pre-download 前把 `sources.url` 换成 `gh-proxy.com` 列表、结束时打印"已还原"，但本次实测**还原未生效**（`git diff` 仍是镜像列表）。提交前必须逐文件 `git diff` 核对 URL 回到官方标量形态（E017 同源问题）。
10. **首轮 `finish` 的 G2 FAIL 与配方无关，是注入的镜像域名本身不可达**：`conan-verify` 把 URL 换成 `ghfast.top/…` 后 `source()` 报 `Connection to ghfast.top timed out`，而同一时刻 `curl` 官方 URL 0.97s 返回 302。**本机侧处置（不入库）**：任务 home 的 `global.conf` 补 `core.sources:download_cache=<绝对路径>/tmp/ch/dlcache`（从模板复制的新 home 默认没有这一行），并把已验证的官方 tarball 按 sha256 预置到 `dlcache/s/<sha>`，sidecar `.json` 的 `references[<ref>]` 里**同时登记官方 URL + `ghfast.top/…` + `gh-proxy.com/…`**（只登记一个会被判 dirty）。补完后 `G2: PASS`，且每次 `conan create` 不再重下。
11. **框架侧三条既有行为，本 PR 未改框架，如实登记**：① G0「干净构建验证」对无 `configure` 的纯 Makefile 项目必报 `configure 失败 (exit 127)`（非阻塞，真正的干净构建证据是 G2 与 W3）；② Step 8 `gen_summary` 抛 `'str' object has no attribute 'append'`，SUMMARY.md 未生成（框架缺陷，按 §9 不得手写 SUMMARY.md）；③ `check_knowledge_gap.py` 把 `manifest.yaml` 的 `knowledge_gained` 条目**按"行内是否含 `ref:` 字面量"** 判是否已被引用（`scripts/ohc/check_knowledge_gap.py:60-66`），因此一条只写了草稿名 + 描述的条目恒被判 `unreferenced`——已在条目内补真实草稿文件路径作为 `ref:` 后消警。另：`conan-verify` 通过后打印"可标记 status: published"——**本任务不采纳**，CI 未 upload 前状态保持 `built`（AGENTS §8）。
---

**编译结束**: 2026-09-26 15:55
**最终状态**: built
