# puredata 0.56.5 鸿蒙 PC 适配说明

## 源码

- 上游项目：https://github.com/pure-data/pure-data
- 版本：0.56.5（上游 tag：`0.56-5`）
- 下载地址：`https://codeload.github.com/pure-data/pure-data/tar.gz/refs/tags/0.56-5`
- SHA-256：`95d3e31cc095190a66bdd0eb77760eaf4d26ccae1322c3325aa05b3457d7b66a`

## 构建适配

上游归档只有 `configure.ac`，没有生成后的 `configure`，必须 `autoreconf -fi`。配方按构建主机现场决定自举工具来源：`build_requirements()` 用 `shutil.which("automake")` / `shutil.which("libtoolize")` 探测，探不到才 `tool_requires("automake/1.18")` / `tool_requires("libtool/2.5.4")`（E178：CI worker 的 PATH 有 autoconf 2.72 因而有 m4，但没有 automake/libtool，裸 `autoreconf -fi` 死在 `Can't exec "aclocal"`；开发机一般整套都有），`_bootstrap_env()` 只把实际解析到的 build-requirement 的 `bin` 前置进 PATH、并把 `PERL5LIB` 限制为 automake 的纯 perl 模块目录（automake 包装脚本 shebang 走系统 perl，混进 conan perl 的 XS 库会崩）。真机走宿主分支（Harmonybrew 的 m4 1.4.21、autoconf 2.73、automake 1.18.1、libtoolize 2.6.2 均已实测可用），CI worker 走制品仓分支，两份环境共用同一份配方。配方通过 `AutotoolsToolchain.generate()` 将 profile 的 clang 显式交给 Autotools，并按 E205 修补 config.guess/config.sub，使设备原生检测返回 `aarch64-unknown-linux-ohos`；不使用 `--build/--host` 绕过识别。

m4 与 autoconf 不写进 `tool_requires` 的依据是真机测出来的：本 profile 解析到的是 conancenter 的 recipe revision（`m4/1.4.19#1727f439` → 包 `579a4b17…`、`autoconf/2.72#e2324a34` → 包 `8c781e33…`），制品仓对这两个包 ID 没有二进制（它们的 OHOS 包挂在另一条 revision：`m4#9a84a566`、`autoconf#ded5821b` → 包 `6b129b068851896169fae42d399fa922d239ce8a`），`--build=missing` 于是转入源码构建，并死在这两个依赖**自身**的 configure——其随包的 `config.guess(2021-05-24)` 不认识 HarmonyOS，退回编译器探测时往 TMPDIR 写 `dummy.c` 被 HMDFS 拒绝（`cannot guess build type; you must specify one`，E114/E136 同类）。另有一条宿主分支必然存在的实测理由：制品仓 automake 包的 `bin/aclocal` 包装脚本 shebang 写死 `#!/data/service/hnp/bin/perl`（worker 侧 HNP perl），这台桌面真机没有 `/data/service/hnp/bin`，直接用它会报 `No such file or directory`、`autoreconf` 退 126。

OHOS 的 HMDFS 临时目录权限问题通过把 `TMPDIR` 指向 Conan build 目录、并将生成 configure 中临时目录 umask 从 077 放宽为 000 处理。旧 `config.guess` 无法识别 `uname -s=HarmonyOS`，其编译器探测还会在 HMDFS 临时目录写 `dummy.c` 失败；配方调用随包导出的 `patch-autotools-ohos.pl` 更新 config.guess/config.sub，让原生检测返回 `aarch64-unknown-linux-ohos`，遵循 E205，不以 `--build/--host` 绕过探测。

portaudio 补丁将 Linux ALSA hostapi 源放在 Automake `ALSA` 条件内，configure 显式传 `--disable-alsa`（上游只有 `AC_ARG_ENABLE([alsa], [--disable-alsa])`，没有 `--without-alsa`；真机也没有 `libasound`，`AC_CHECK_LIB` 同样会把 `alsa` 判为 no，显式传参只是把这件事固定下来）；线程取消路径改为按 libc 能力门控：`configure.ac` 用 `AC_CHECK_FUNCS([pthread_cancel])` 在探测成功时向 `PD_CFLAGS` 追加 `-DHAVE_PTHREAD_CANCEL`，`pa_unix_util.c` 的 4 处 `#ifdef PTHREAD_CANCELED` 变为 `#if defined(PTHREAD_CANCELED) && defined(HAVE_PTHREAD_CANCEL)`（遵循 E407，不在源码/补丁中引入平台条件编译宏）。声音设备端到端测试不在本次覆盖范围内。

## 评审意见闭环（AI 检视 P1/P2/P3）

- **P1/P3（`patch-autotools-ohos.pl`）**：步骤 2.3 的守卫 `unless ($sc =~ /linux-ohos/)` 是对整个文件内容做子串匹配，而步骤 2.1 的替换文本本身就写入字面量 `basic_os=linux-ohos`，因此 2.1 一旦成功，2.3 必被跳过；第 132 行的自检 `$ok++ if $sc =~ /linux-ohos/` 用同一过宽正则，会以 `Score ≥ 4 ✅ Patching successful` 报假绿。守卫与自检均改为只认列表成员形式 `/linux-ohos\*/`。
  - 复现（旧式 config.sub 夹具：含 `android-linux)` 三元组块、kernel-OS 列表只有 `linux-uclibc*-`）：旧脚本打印 `[skip] linux-ohos already present`，结果文件的列表仍是 `linux-uclibc*- )`，却输出 `Score: 4/5 ✅ Patching successful`；新脚本打印 `[ok] Added linux-ohos to kernel list`，结果变为 `linux-uclibc*- | linux-ohos*)`。
  - 无回归（本配方实际使用的 GNU config）：`autoreconf -fi` 复制进来的是 automake 1.18.1 的 `config.sub`，`timestamp='2024-05-27'`，其 kernel-OS 校验列表**上游已含** `| linux-ohos*-`。在真机上对同一份 pristine 文件分别跑旧/新脚本，两者都打印 `[skip]`、`Score: 4/5`、退出码 0，产物列表同为 `| linux-uclibc*- | linux-ohos*- )`；两份产物执行 `config.sub "$(config.guess)"` 都返回 `aarch64-unknown-linux-ohos`。⇒ 本库的构建结果不因该修改而改变，AI 推断的「configure 直接失败」在本版本不发生（该后果只在缺 `linux-ohos*-` 的旧 config.sub 上成立，与既有条目 E268/E122 的记录范围一致）。
- **P2（`0002`）**：原补丁用 `!defined(__OHOS__)` 平台条件编译宏，违反仓规 R8；按 E407 换成 configure 期 `AC_CHECK_FUNCS([pthread_cancel])` 能力探测（见上节），补丁随之改名 `0002-portaudio-pthread-cancel-feature-gate.patch`。

## 测试统计与设备验证

- 上游归档没有 `tests/`，全部 14 个 `Makefile.am` 未注册 `TESTS`、`check_PROGRAMS` 或 `noinst_PROGRAMS`；automake 仍会生成 `check` 目标，但它不执行任何测试程序。取数命令：`grep -rn -E '(^|[^A-Za-z_])(TESTS|check_PROGRAMS|noinst_PROGRAMS)[[:space:]]*[+]?=' --include=Makefile.am . | wc -l` → `0`。上游独立自动化测试数为 0。
- `libpd/test_libpd/` 是独立手写 makefile（自述假设 libpd 已在 `../` 构建好），不被任何 `Makefile.am` 引用；libpd 本体由 `--enable-libpd`（`AM_CONDITIONAL(LIBPD)`）控制，本配方未开启，故本构建树既不编译也不运行它。
- 用例口径：按脚本自己打印的 `PASS:` 行计数，一个文件不等于一个用例。取数命令 `grep -c '^PASS:'` → 5。
- HarmonyOS 设备命令：`CONAN_HOME=~/work/psj/ch-pd13882 conan create archives/p/puredata/0.56.5 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`。
- 设备实测（评审修改后的复验）：`CREATE_EXIT:0`；消费者/平台用例 **5/5 PASS**（`test.sh` 4 项：`pd -version` 退出 0、headless `-nogui -nosound -send "; pd quit;"` 启动调度器并解析 FUDI 后退出 0、`pdsend`/`pdreceive` 在 PATH、包内数据目录 `lib/pd` 存在；`test_ohos/run_ohos_test.sh` 1 项：AArch64 ELF 且解释器为 `ld-musl-aarch64.so.1`），末行 `[test] all PASS`。
- 能力探测实测：configure 日志 `checking for pthread_cancel... no` ⇒ 不追加 `-DHAVE_PTHREAD_CANCEL`，PortAudio 走 join 回退路径（与改前 `!__OHOS__` 的效果一致，但判据来自探测而非平台名）。
- `install-exec-hook` 报 `Makefile:4425: install-exec-hook] Error 1 (ignored)`：日志原文是 `ln: Unknown option 'relative'`——设备上 Toybox `ln` 不支持 `--relative`。失败的是上游 `src/Makefile.am` 中带 `-` 前缀的那条**回体积软链尝试**（其上一行的绝对软链已成功，上游注释也写明 "try to create relative symlinks (doesn't work on macOS)"），因此 make 记为 ignored，不影响 `CREATE_EXIT:0` 与包内容。

## 关联

- 任务：#9812
- 路径 B 知识议题：#3618
- PR：#13882
