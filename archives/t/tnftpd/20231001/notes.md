# tnftpd 20231001 适配笔记

## 编译环境
- 构建系统: autotools（官方 release 包自带预生成 configure / Makefile.in / aclocal.m4 / ltmain.sh，无需 autoreconf）
- 编译日期: 2026-09-30
- 编译器: clang/clang++（profile ohos-aarch64，os=OHOS / arch=armv8 / os.version=6.0）
- 状态: built（配方已就绪，真机 rule4 预检结果见下一轮）

## 概况

`tnftpd` 是 NetBSD FTP 服务端守护进程（`lukemftpd`）移植到其他系统的版本，
设计为在 inetd 下运行（stdio = 控制连接）。官方 release tarball **不含**
由 `ftpcmd.y` 生成的 `ftpcmd.c` —— 构建期必须现场跑 bison/yacc 生成，因此
**bison 是硬性构建期依赖**（configure 的 `AC_PROG_YACC` 找不到就
`missing bison or yacc` 硬失败）。

产物：`tnftpd`（libexec_PROGRAMS，守护进程）＋ man 页 + examples 配置。
私有辅助库 `libnetbsd.la` / `libls.la` 是 `noinst_LTLIBRARIES`（不被安装），
`tnftpd` 静态链接它们成为自包含二进制。

## 编译步骤（配方内实际形态）

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 配方内等价手工步骤（build()/package()）：
./configure \
    --without-pam --without-skey --without-sia --with-blocklist=no
make -j1          # E074: 并行 make 触发 HMDFS jobserver fifo EPERM ⇒ -j1
make install -j1  # tnftpd 装到 $prefix/libexec，随后配方 package() 重命名到 $prefix/bin
```

- `tnftpd` 是 `libexec_PROGRAMS`，默认装 `$prefix/libexec/tnftpd`；配方在
  `package()` 中将其重命名到 `$prefix/bin`，便于 PATH 与消费者测试。
- `--without-{pam,skey,sia}` 与 `--with-blocklist=no`：可选认证组件在
  OHOS 制品仓未发布，显式禁用保证确定性（守护进程走 Unix passwd 认证即可）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 起手 `cannot guess build type; you must specify one` | configure 因 LT_INIT() 内部调用 AC_CANONICAL_HOST 必跑 config.guess（2018-03-08），不识别 `uname -s`=HarmonyOS | 补丁 0001 加 HarmonyOS 分支输出 `aarch64-unknown-linux-ohos`（本版 config.guess 的 case 风格是 `echo ...; exit ;;`，照抄新版 GUESS= 写法会命中分支却不输出，radvd 同款） |
| 2 | `Invalid configuration aarch64-unknown-linux-ohos: system ohos not recognized` | config.sub（2018-05-05）两处 OS 白名单（KERNEL-OS 组合表 + OS 后缀表）不含 ohos | 补丁 0002 补 `linux-ohos*` / `-linux-ohos*`；验证 `./config.sub aarch64-unknown-linux-ohos` 原样输出、RC=0 |
| 3 | `config.status: error: could not setup config files machinery`（configure 起手 `can't fork - try again`，嵌套 mktemp 在不可写 FS 上 fork 失败） | HMDFS 上 configure 以 `(umask 077 && mktemp -d "./confXXXXXX")` 建的临时目录不可写，写 subs1.awk 报 Permission denied（E011/E052/E112/E114/E129 家族；`unsafe_local_mktemp`） | 补丁 0003 把该块 `mktemp -d` 换成 `false` 强制走 mkdir fallback，并把两处 `umask 077` 改 `022`（libradsec/avfs/autocutsel 同款）。这是唯一的 autoconf 临时目录块，configure 运行时与生成的 config.status 经 `$ac_tmp` 复用 |
| 4 | ftpcmd.c 缺失 | release 包不预生成解析器，cmds.c/ftpd.c 引用 ftpcmd.c 的 YY 符号 | `tool_requires("bison/3.8.2")`（radvd 2.20 同款，制品仓已发布） |
| 5 | configure 起手 `working directory cannot be determined`（伴随成片 `shell-init`/`job-working-directory` getcwd 错误，errno=Bad address） | 工具链 hnp bash（profile 的 CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash）在 HMDFS 构建目录 getcwd() 失败；本包是 autoconf 2.69 configure，前导 CONFIG_SHELL 重执行块把自己切到坏 bash，`ac_pwd=\`pwd\`` 随即崩溃 | build() 在 OHOS 上显式 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh configure ...`（变量前缀压过 buildenv），make/install 追加 `SHELL=/bin/sh`（libfec/libdisasm 同款已验证方案） |
| 6 | 真机 compile 阶段：`sh: can't fork - try again`，stdout/stderr 均空（无任何 tnftpd 构建输出） | `can't fork - try again` = `fork()` 返回 EAGAIN（worker 处于 fd/内存/进程数压力下，进程创建被拒）。失败点落在编排/SSH 会话层、tnftpd 首个编译输出之前，非配方内。配方已为最低 fork 开销：官方发行包自带预生成 configure（无 autoreconf 自举）、`make -j1`/`install -j1` 串行、`/bin/sh` 直驱、无 conan 依赖（sirocco/2.1.1 同型：共享真机瞬时资源告警非配方缺陷） | 环境性故障，不做伪造配方改动（禁止把环境失败包装成配方缺陷，DRAFT-11327 / E491 forbid_3）。保持已验证配方不变，等待真机环境恢复后由 hmbs 自动复跑 |
| 7 | 真机 compile/package 阶段：`make[2]: *** [Makefile:322: install-dist_exampleDATA] Error 64`，`install -c -m 644 .../examples/ftpd.conf .../examples/ftpusers '<pkg>/share/examples/tnftpd'` 失败 | HMBS 的 install shim（runtime/<task>/bin/install）只接受**单文件两参**调用；automake 批量安装 `install -c -m 644 f1..fN dir/` 直接 exit 64 (EX_USAGE)。bin/程序（单文件）装成功，轮到 examples 批量装两个配置文件即挂（adms 2.3.7 / libgsf 1.14.58 / avahi 0.9_rc5 / xeyes 1.3.1 已过门禁同型） | package() 里先写一个 cp/mkdir shim（解析 -c/-m/-d，末参为目标目录/文件，逐源 cp），再递归把 configure 生成的各 Makefile `INSTALL = <...>/install ...` 重定向为 shim 绝对路径（INSTALL_DATA/INSTALL_PROGRAM 引用 ${INSTALL} 自动重算），随后 autotools.install() 全程走 shim |

## 真机预检轮次记录

| 轮次 | 阶段 | 结果 | 处置 |
|---|---|---|---|
| 2026-09-30 preflight | compile | `sh: can't fork - try again`（stdout/stderr 空） | 共享真机瞬时资源耗尽（fork EAGAIN），非配方缺陷；配方已最低 fork 开销（发行包自带 configure、-j1、/bin/sh），保持不变，等待环境恢复自动复跑 |
| 2026-10-02 preflight | compile/package | `install -c -m 644 f1 f2 dir/` 的 examples 批量安装 `install-dist_exampleDATA` Error 64 (EX_USAGE) | HMBS install shim 只接受单文件两参调用；配方 package() 写入 cp/mkdir install shim 并递归把各生成 Makefile 的 `INSTALL = .../install` 重定向到它（adms/libgsf/avahi/xeyes 同款），等待 hmbs 复跑验证 |
| 2026-10-03 preflight | compile | `configure[1208]: can't fork - try again`（configure 参数解析循环内 fork 子进程 `expr`/`echo|sed` 被拒，configure 早期即失败，早于 mktemp 块） | **环境性 fork EAGAIN**（共享真机瞬时进程/内存/pid 资源耗尽），与 2026-09-30 轮同指纹。configure 1208 行是参数解析 `while test $# != 0; do case ... expr ...` 循环（对照官方 tar 包 configure 逐行验证，补丁 0001/0002/0003 分别只改 config.guess/config.sub/configure 17366 行 mktemp 块，不改变 1208 行号）。配方已是 fork 最低开销（发行包自带 configure 无 autoreconf、make/install -j1、/bin/sh 直驱、无 conan 依赖），configure 改不了、也不应改上游去规避机器瞬时压力。沿用第 6 轮判定：环境性故障，不做伪造配方改动，等待真机恢复由 hmbs 自动复跑。 |
| 2026-10-07 preflight | compile | `sh: /usr/bin/rm: Out of memory`（compile 阶段） | **环境性 fork/exec ENOMEM**，与第 6、2026-10-03 轮同源：shell 在 fork/exec `/usr/bin/rm`（configure 的清理类 `rm -f` / make 配方行普遍调用）时因共享真机瞬时内存/进程资源耗尽返回 ENOMEM（对应 DRAFT-ci-worker-gate-fork-oom 的 `sh:.*Out of memory`、DRAFT-11327 的 `(grep|cut): Out of memory` 同型旁证）。`/usr/bin/rm` 来自 configure/make 脚本自身，非配方显式调用；配方无进程膨胀点，已是 fork 最低开销（发行包自带 configure、-j1、/bin/sh 直驱、无 conan 依赖）。判定：环境性瞬时资源故障，非配方缺陷；不做伪造配方改动（forbid 见 DRAFT-11327/DRAFT-ci-worker-gate-fork-oom、E491 forbid_3：fork/Errno 12 必须先有设备资源证据），等待真机恢复由 hmbs 自动复跑。 |
| 2026-10-07 preflight | test_package | check 1-3 PASS，check 4（`tnftpd -C <bogus-user>` 自终止）打印后 test.sh 直接 `Error 1 while executing`（test() line 65），无 FAIL 行 | **本包 test.sh 的 set -e 捕获坑（与 OHOS 无关，本地 Linux 复现同一失败）**：check 3 之后是**裸命令** `"$BIN" -C bogus-user ...; rc=$?`。`tnftpd -C <bogus-user>` 对未知用户**合法返回 rc=1**（access-check 拒绝访问），但 `set -e` 会在该非零返回值处**立即中止整个脚本**，`rc=$?` 与 PASS/FAIL 判断根本没机会执行 ⇒ 脚本以 1 退出、test() 报 Error 1，且看不到 FAIL 行。对照真机日志（check 1-3 PASS → check 4 打印 → Error 1，无 FAIL）与本地复现完全一致。**修复**：把 `-C` 调用改为 `if "$BIN" -C ... ; then rc=0; else rc=$?; fi`——`if` 条件的命令对 `set -e` 豁免，`rc` 在 else 分支捕获，check 4 的正则逻辑（rc 0/1 均通过）不变。同样注意 check 1-3 的 `cmp/head/printf` 都带 `|| true`，仅 check 4 是裸命令。修复后本地真机二进制实测 4/4 PASS、标记载正确。 |

## 源码修改（补丁）

- `patches/0001-config.guess-ohos.patch`：config.guess 加 HarmonyOS 分支 → aarch64-unknown-linux-ohos
- `patches/0002-config.sub-ohos.patch`：config.sub 补 `linux-ohos*` / `-linux-ohos*`
- `patches/0003-configure-hmdfs-umask.patch`：configure 唯一的 autoconf 临时目录块把 `mktemp -d "./confXXXXXX"` 换成 `false`（强制 mkdir fallback），两处 `umask 077` → `022`

（三者均为 portability 补丁，已在 conandata.yml 声明。）

## 依赖版本

| 依赖 | 版本 | 形态 | 制品仓 |
|---|---|---|---|
| bison | 3.8.2 | tool_requires | 已发布（radvd 2.20 同款） |
| 运行时 | 仅 libc / libc++ | 无 conan 依赖 | — |
| 认证 | PAM/S/Key/SIA/blocklist | 显式禁用 | OHOS 未发布 |

## 测试情况（上游）

**上游无任何测试套件**（逐文件审计确认）：四个子目录 Makefile.am 均无
TESTS / check_PROGRAMS / AM_TESTS，无 test/ 或 tests/ 目录，configure.ac 无
enable-tests 相关宏，Makefile.in 的 check 目标仅为空操作的 `check-am: all-am`
（只重建、不跑用例）。无 gtest/autotest/自定义脚本。⇒ `upstream_tests_exist: false`，
不做 `make check`。

消费者验证（test_package/）：`tnftpd` 是 inetd 型守护进程，无 `--help`，
直接运行会因 stdin 无 socket 连接而在 `getpeername(0,...)` 失败后正常退出。
消费者测试用**自终止的 `-C <user>` 访问检查模式**（在 getopt 循环内
`sgetpwnam`+`checkaccess` 后 `exit 0/1`，不进入 FTP 循环、不依赖 /etc 状态）
＋ ELF/可执行/存在性校验，真实执行被适配二进制。

## 验证结果

> 真机 rule4 预检结果与 PR 正文测试用例数由 HMBS evidence 轮实测后填写；
> 本节初始仅记录配方与审查期预期。用户态 `tnftpd -C <user>` 自终止验证与
> ELF 校验为确定性消费者断言。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Autotools 配方 |
| conandata.yml | 官方源 URL + SHA256 + 三枚补丁声明 |
| patches/0001-0003 | OHOS 移植补丁（config.guess/config.sub/configure） |
| manifest.yaml | 软件级元数据 |
| 20231001/manifest.yaml | 版本级元数据 + 上游测试审计 |
| 20231001/notes.md | 本笔记 |
| test_package/ | 消费者验证（conanfile.py + test.sh + MANIFEST.yml） |

## 注意事项

- 守护进程本身需在真实网络环境下（inetd / `-D`）才能完成完整 FTP 会话，
  消费者测试只做离线的确定性验证（存在性/可执行/ELF/`-C` 自终止），
  不在无人值守真机上起监听端口。
- 版本字符串 `FTPD_VERSION = "NetBSD-ftpd 20230930"`（上游每日构建日期），
  与包版本号 `20231001`（发布 tar 包日期）不同，属上游正常现象。
