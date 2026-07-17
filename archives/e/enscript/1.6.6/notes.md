# enscript 1.6.6 — HarmonyOS PC 适配笔记

## 概述
- 三方库：GNU enscript 1.6.6（ASCII 文本 → PostScript/HTML/RTF 等转换工具）
- 类型：命令行工具，构建产物 `enscript`、`mkafmmap`、`states`、`diffpp`、`over`、`sliceprint`
- 构建系统：autotools（configure + make），预生成的 lex/yacc 产物随源码分发，无需 flex/bison
- 依赖：无外部三方库依赖，产物仅链接 `libc.so`（musl）
- 目标平台：OHOS aarch64（armv8），clang 15 / libc++

## 配置选项
- `--disable-nls`：关闭 NLS，避免依赖 OHOS musl sysroot 中不存在的 libintl/gettext
- `SHELL=<bash>`：OHOS 无 /bin/sh，configure/libtool 需 bash（R5）

## 适配问题与修复

### 0. E007 — config.guess/config.sub 不识别 HarmonyOS（需补丁）
真实 OHOS worker 的 `uname -s` 返回 `HarmonyOS`（`uname -r` = "HongMeng Kernel"），
而 enscript 随源码分发的 config.guess（2012-02-10）只识别 `*:Linux:*:*`，
遇到 HarmonyOS 会落到编译器探测兜底分支并失败（且 OHOS `/tmp` 只读，探测写临时文件
被拒），最终 `configure: error: cannot guess build type`。

修复：
- `0001-config.guess-harmonyos.patch`：在主 case 顶部新增 `*:HarmonyOS:*:* | *:OHOS:*:*`
  分支，直接输出 `${UNAME_MACHINE}-unknown-linux-ohos` 并 exit，绕过编译器探测；
- `0002-config.sub-linux-ohos.patch`：让 config.sub 识别 `linux-ohos` 内核-OS 组合，
  接受 `aarch64-unknown-linux-ohos` 三元组。

已在容器内以 `--build=aarch64-unknown-linux-ohos` 实测 configure（host_os=linux-ohos）
+ make 全程通过，libtool/gettext 的 host_os 分支无异常。
（注：本地容器 uname 报 Linux，配方走 conan create 时 config.guess 命中 Linux 分支输出
linux-gnu；HarmonyOS 分支已单独实测，二者构建结果一致。）

### 0.5 E011 — HMDFS 下 config.status umask 077 建目录后无法写文件（需补丁）
真实 worker 的构建目录在 HMDFS 上，config.status 用 `umask 077` 创建临时目录
（0700）后，向其中 `echo ... > confXXXX/subs1.awk` 的重定向被拒
（`config.status: subs1.awk: Permission denied`）。这是 HMDFS 的权限位怪癖。

修复：`0004-configure-hmdfs-umask.patch` 将 configure 内 config.status 临时目录
创建处的 `umask 077` 改为 `umask 022`（目录 0755）。为纯写入重定向，与文件可执行位
无关。与 gnu-which 的 E011 修法一致。（本地容器非 HMDFS，无法复现，按既有 E011 模式修复。）

### 0.8 OHOS 无 passwd 数据库 — getpwuid 致命失败（需补丁）
enscript 启动时 `passwd = getpwuid(getuid())`，失败即 FATAL 退出
（真实 worker 报 `couldn't get passwd entry for uid=...: Not supported`）。
OHOS musl 不提供 passwd 数据库，getpwuid 恒失败，导致任何 enscript 调用（含
`--version`）在真机上直接退出。

修复：`0005-ohos-passwd-fallback.patch` 在 getpwuid 返回 NULL 时不再 FATAL，
改为从环境变量（LOGNAME/USER/HOME）合成一个 `struct passwd` 回退，令
`pw_name/pw_gecos/pw_dir/pw_uid` 有合理取值。运行期守卫（`if (passwd==NULL)`），
对所有平台安全；已在容器内以未登记 uid（getpwuid 失败）实测 `--version` 正常退出。

（注：本地容器 uid 有 passwd 记录，走正常分支；OHOS 分支已用 `--user <未知uid>` 单独实测。）

### 1. E002 — /tmp 只读导致 PostScript 生成失败（需补丁）
enscript 在 `divert()`（psgen.c）和 `--toc`（main.c）路径下用 libc `tmpfile()`
创建临时文件。musl 的 `tmpfile()` 硬编码在 `/tmp` 下创建，而 OHOS `/tmp` 只读，
调用失败后 enscript `FATAL` 退出（"couldn't create temporary divert file"）。
即使一次普通的 文本→PS 转换也会走 divert 路径，因此必须修复。

修复：补丁 `0001-ohos-tmpdir-aware-tmpfile.patch` 在 util.c 新增可移植的
`xtmpfile()`，优先在 `$TMPDIR`/`$HOME` 下用 `mkstemp` 创建并立即 `unlink`
（保持 tmpfile() 的匿名语义），无可写目录时回退到 libc `tmpfile()`；
将 psgen.c/main.c 两处 `tmpfile()` 调用改为 `xtmpfile()`。该改动对所有平台安全。

### 2. E010 — toybox 缺 expr/awk（环境侧，无需改配方）
OHOS 默认 toybox 未提供 `expr`/`awk`，enscript 1.6.6 老版本 autoconf 生成的
configure/config.status 依赖二者（缺 expr 时 configure 自重入陷入死循环并 SIGSEGV）。
CI 构建镜像已预装 GNU coreutils / gawk（见 E010），configure 正常通过；
配方本身无需声明，与仓内其他 autotools 配方一致。

### 3. 运行期数据路径重定位
enscript 编译期硬编码 SYSCONFDIR / library 路径（`/share/enscript`、`/etc`），
Conan 重定位包后该路径失效。`package_info()` 通过 `runenv_info` 导出
`ENSCRIPT_LIBRARY=<pkg>/share/enscript`，enscript 借助其
`<library>/../../etc` 回退逻辑定位 `enscript.cfg`，保持包可重定位。

## 本地容器构建验证（CI 同源）
- `conan create ... -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64` 成功
- test_package 真实运行：`enscript --version` + 文本→PostScript 转换，输出为合法
  `%!PS-Adobe-3.0` 文档（约 11.5 KB）
- 产物 `bin/enscript`：ELF64 / AArch64 / PIE，`NEEDED` 仅 `libc.so`

## 测试说明
enscript 上游未提供断言式回归测试套件（无 `make check`）。test_package 从消费者
视角实测核心功能：调用二进制完成一次真实的文本→PostScript 转换并校验输出头与非空，
符合 R34（实质调用被测包）。
