# uucp 1.07 adaptation notes

## Build configuration

- Build system: Autotools（autoconf 2.13 + automake 1.4 预生成 `configure`/`Makefile.in`，
  in-source 构建，无 autoreconf）。
- Packaged programs: `uucico` `uuxqt` `uuchk` `uuconv`（sbin）+ `uux` `uucp` `uustat`
  `uuname` `uulog` `uupick` `cu`（bin）+ `uusched` `uuto`（sh 脚本）= 13 个 bin 产物。
- Packaged data: 4 个 man1 页、2 个 man8 页、`share/info/uucp.info`、`licenses/COPYING`。
- Conan dependencies: **none**。`configure.in` 无 PKG_CHECK_MODULES/AM_PATH_*/
  AC_MSG_ERROR。5 条 AC_CHECK_LIB（sun/nsl_s/nsl/socket/xti）均为**可选且非致命**探测
  （AC_CHECK_LIB 失败只会把该库排除出 LIBS）；其中 nsl_s/nsl/socket/xti 4 条位于
  `case $LIBS in ... ;; *)` 守卫内，命中同族库即短路；`sun`（configure.in:64）为顶层
  裸探测。链接面 `LDADD = unix/libunix.a uuconf/libuuconf.a lib/libuucp.a` 三者均为
  包内 `noinst_LIBRARIES`。
- Source URL: `conandata.yml` 的 `sources.url` 为镜像列表（TUNA/USTC/Aliyun
  优先、GNU 官方 `ftp.gnu.org` 兜底），由 CI 的 Mirror fallback 步骤自动改写
  （`ci/conan/build_and_test.sh`）。Conan 2.x `get()` 原生支持 url 列表，逐个
  尝试直到 sha256 校验通过；官方源与 sha256 未变。
- Platform libraries: libc only（socket 函数 musl 内置；`-lsocket/-lnsl/-lxti/-lnsl_s`
  探测全部 no 后由 libc 符号兜底，configure 实测 `checking for socket... yes`）。

## OpenHarmony adaptation

无源码补丁（`patches: {}`）。三项适配全部通过构建策略完成：

1. **交叉模式天然兼容**：autoconf-2.13 生成的 configure 在 "C compiler works"
   检查里只要求链接成功；`./conftest` 无法执行仅置 `cross_compiling=yes` 不报错。
   本机实测 conftest 可直接执行（`is a cross-compiler... no`），6 处 AC_TRY_RUN
   全部走真实运行路径：`ftime works correctly... yes`、`statvfs... yes`
   （STAT_STATVFS 命中使 statfs 系列链短路）。
2. **绕过安装钩子**：`Makefile.am:79-94` 的 `install-exec-hook` 执行 `chown $(OWNER)`
   （`Makefile:75` 得 `OWNER = uucp`）并在其 `HAVE_MKDIR=0` 兜底分支执行 `chown root`；
   非 root 构建用户向他人 chown 必然 EPERM，故不跑 `make install`，`package()` 显式
   复制产物并 chmod 0755。（同钩子内的 `chmod 4555`/`chmod 100` 本身并非阻断项：属主可对
   自有文件置 setuid，且 `chmod 100` 的 uudir 分支因 `config.h` 中 `HAVE_MKDIR 1` 不会
   被走到。）
3. **makeinfo 免依赖**：`all-am` 依赖 `$(INFO_DEPS)`；build() 在 make 前检查
   `uucp.info`/`uucp.texi`/`Makefile.am` 时间戳并对过期生成物 `touch`，保证 automake
   规则不尝试重建（宿主无 makeinfo/autoconf/automake，且 `uucp.info` 随 tarball 发布）。

configure 选项 `--prefix=/ --sbindir=/bin --bindir=/bin --mandir=/share/man
--infodir=/share/info` 仅影响 `uusched`/`uuto` 脚本内的 @SBINDIR@/@BINDIR@ 替换与
NEWCONFIGLIB 默认文本；实际安装由 package() 显式布局。

## Tests

- 上游自动化测试：**0 用例**。automake-1.4 的 `check: check-recursive → check-am:
  all-am` 无 TESTS 变量；`make check` 已在 build() 真实执行
  （`reports/upstream-check.log`：lib/uuconf/unix 三子目录均 "Nothing to be done
  for 'check'"）。
- 上游手工测试驱动 `tstuu.c`（noinst_PROGRAMS）：已验证编译产出（43392 B ELF），
  但其回环测试需 fork uucico + setuid uucp 用户 + spool 目录写权限，OHOS 构建用户
  无法满足，按环境归因登记、不计入用例统计。
- test_package（消费者用例，OHOS 真机执行，18 断言全过）：
  1. 11 个程序的 `-v` 版本横幅（exit 0 且含 `Taylor UUCP) 1.07`）；
  2. `uusched`/`uuto` 存在、可执行、`sh -n` 语法有效；
  3. `uname -m` = aarch64 平台断言；
  4. **OHOS 消费者功能用例**：临时目录构造 `config → sysfile → sys → portfile →
     port(TCP)` 完整配置链，`uuchk -I` 解析整条链并打印系统定义、`-s` 按名检索、
     非法系统名退出非零、`uuname -I -l` 读出 nodename —— 与 uucico 启动时相同的
     uuconf 解析代码路径。

## Environment notes

- 第 1 轮构建失败为 agent 会话特有环境泄漏：工作台主进程把
  `cli/vendor/shim/safe-bin` 注入 PATH 首位，automake 规则硬编码的 `rm -f` 命中
  该垫片（shebang `/bin/bash` 在本机不存在 → Error 126）。启动 conan 前清洗 PATH
  后消失；CI 环境无此垫片，与配方无关（证据：reports/conan-create-r1-env-leak.log）。
- 第 2 轮为首个全绿构建，test_package 16/18：消费者用例误用 `sysdir` 指令名
  （uuconf `tinit.c` 指令表仅 `sysfile`/`portfile`）；更正后第 3 轮 18/18
  （reports/conan-create-r2-first-green-build.log 留档）。
- 第 4 轮：`conandata.yml` 被 CI Mirror fallback 改写为镜像列表后重跑 create（18/18）。
- 第 5/6 轮：依独立审计意见修正本文档与配方 docstring 的两处表述（AC_CHECK_LIB 守卫范围、
  make install 阻断归因）后重跑；r5 起 recipe revision 稳定为 `830ab91b71`，r6 为最终权威轮
  （`CREATE_EXIT=0`、test_package 18/18，日志 reports/conan-create.log）。
- W3 本地 CI（含 JC 门禁与内嵌 create）在第 5 轮之后运行并全绿（reports/w3-local-ci.log，
  对齐 revision `830ab91b71`）；第 6 轮为在其之后的**最终归档重跑**——因为 `conan-verify`
  的 G2 闸会自行重写 reports/conan-create.log（把完整日志顶成"缓存命中"短日志），所以
  权威日志的归档刻意放在全部 verify/finish 之后。
- 注意：`reports/` 与 `packaging/` 均为 gitignore 的本地证据，不进 PR。
---

**编译结束**: 2026-09-20 21:22
**最终状态**: built
