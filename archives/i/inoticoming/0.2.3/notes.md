# inoticoming 0.2.3 适配笔记

## 编译环境

- 构建系统: autotools（发行包自带 configure / Makefile.in / ac 辅助脚本，无需 autoreconf）
- 编译日期: 2026-09-23
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos，取自 Conan conf，非 shell 裸变量）
- 平台: HarmonyOS / HongMeng Kernel 1.12.0 aarch64；Conan 2.29.1；profile `ci/conan/profiles/ohos-aarch64`
- 状态: built（本地 conan create/G2 通过，W3 本地 CI 通过；未上传制品仓）

## W0 依赖检查

inoticoming 0.2.3 **无任何第三方依赖**（编译期与运行期均只有 libc）：

- `configure.ac` 只有 `AC_PROG_CC` / `AC_PROG_INSTALL` / `AC_SYS_LARGEFILE` /
  `AC_CHECK_FUNCS([closefrom])` / `AC_CHECK_HEADERS(sys/inotify.h …)`，不探测任何外部库。
- 源码仅 `inoticoming.c` + `closeallfds.c`，使用 stdio/stdlib/unistd/poll/dirent/regex/
  getopt/syslog/signal/wait 与 inotify 接口。
- Debian 控制文件 `Build-Depends: debhelper (>= 10)`（打包工具，非库依赖）。

`bash ci/scripts/preflight_check.sh inoticoming/0.2.3` → `[OK] 预检通过（无依赖需要检查）`。

## W0b 历史核验

- 本仓库无 `archives/i/inoticoming` 历史归档（`BUILD_HISTORY_FOUND=False`），无历史 notes 可参照。
- 同类平台知识：`archives/i/inotify-tools/4.25.9.0`（同为 inotify 用户态工具）记录
  **"OHOS 支持 sys/inotify.h 且 inotify_init() 正常工作；OHOS 不支持 fanotify"**。
  本次实测确认：`inotify_init()`/`inotify_add_watch()` 返回正常 fd，**内核投递
  IN_CLOSE_WRITE/IN_MOVED_TO 正常**，故 inoticoming 的全部上游功能可用，无需禁用任何功能。
- 命中 E011/E129（HMDFS umask 077 → `config.status` 无法建临时目录），见"问题与解决"。

## 编译步骤

探索阶段（模式 B，`source .build-context-inoticoming-0.2.3` 后手工执行）：

```sh
cd $BUILD_SRC_DIR
sed -i 's/umask 077/umask 022/g' configure     # E011，改源文件 + 记 notes（R1）
./configure --prefix=$DEFAULT_PREFIX           # 退出码 0（日志 reports/step2-configure.log）
make -j1                                       # 退出码 0，无 warning（reports/step2-make.log）
make check                                     # 退出码 0，无输出（0 用例，reports/step2-make-check.log）
make install DESTDIR=$TEST_PREFIX              # bin/inoticoming + share/man/man1/inoticoming.1
```

固化阶段（配方，`conan create` 自动）：

```sh
conan create archives/i/inoticoming/0.2.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

配方用 Conan `Autotools`/`AutotoolsToolchain`：`configure`（工具链自动注入
`--prefix=/` 与 `--bindir/--sbindir/--libdir/--includedir/--oldincludedir`，
本包不追加任何选项，未使用 `--build/--host/--target`）→ `make -j1` → `make check -j1` →
`make install DESTDIR=<package_folder> -j1`，另复制 `COPYING` 到 `licenses/`。
（三个 make 步骤都传 `-j1`：并行 make 在 OHOS 上会触发 E074 jobserver mkfifo 警告；
`Autotools.install(args=["-j1"])` 仍会自动补上它自己的 `DESTDIR=`——只有 args 里
不含 `DESTDIR=` 时才插入。）
产物：`bin/inoticoming`、`share/man/man1/inoticoming.1`、`licenses/COPYING`。

## 遇到的问题与解决方案

| # | 问题（首个错误行） | 根因 | 解决方案 | 重新验证 |
|---|-------------------|------|----------|----------|
| 1 | `./config.status: line 627: ./conflIlfkJ/subs1.awk: Permission denied` / `config.status: error: could not setup config files machinery`（退出码 1） | E011：HMDFS 把新建目录 owner 映射为 uid 20001006 并保留 setgid 位，autoconf 的 `(umask 077 && mktemp -d "./confXXXXXX")` 得到 `drwx--S---`，构建用户（uid 20020101）无法写入自己的临时目录 | 把 `configure` 的 `umask 077` 放宽为 `umask 022` 并固化为 `patches/0001-configure.patch`（`refresh-patch --auto` 生成，conandata.yml 声明）；configure 生成 config.status 时随之生效 | 补丁应用日志 `Apply patch (portability): Relax umask 077…`；`conan create` G2 PASS |
| 2 | 修丁后**同一错误一字不差复现**（`conan create` 第二轮仍失败，无任何新报错） | `basic_layout` 的 build 目录是 `build-<build_type>`（Release → `build-release`），与 source 目录不同；首版在 `build()` 内联替换时只扫 `self.build_folder`，`os.path.isfile(build_folder/configure)` 恒假 → 替换被**静默跳过**，configure 根本没被改到 | 改为"补丁作用于 source_folder"（首选，与 layout 无关） | 补丁路线 `conan create` 成功，G2 PASS；连续两轮 W3 均全绿 |
| 3 | 无（上游无测试套件） | `Makefile.am` 无 `TESTS`/`check_PROGRAMS` | 配方仍执行真实入口 `make check`（0 用例），并在 `test_package/MANIFEST.yml` 留完整审计；新增 12 个适配方用例（6 消费者 + 6 鸿蒙专项） | `make check` 退出码 0；test_package 12/12 通过 |
| 4 | `clean-verify`(G0) 报 `configure: error: invalid variable name` / `invalid host type: []` | 框架工具 `scripts/ohc/clean_verify.py:73` 用正则 `configure_options:\s*["\']?(.*?)["\']?\n` 解析 manifest，把空列表 `[]` 当成字面量 `[]` 传给 configure（并会 lstrip 掉选项前导 `-`）；这是工具解析缺陷，非本包问题 | 未改框架文件（W2：框架修改须单独 PR）。G0 在 finish 中为**非阻塞**步骤；本包以 `conan-verify` + `W3 build_and_test.sh`（= CI 同口径）作为权威验证 | W3 全绿（JC/KC/L0-L5 pass，test_package 12/12）；G0 仍为工具限制（已如实记录） |
| 5 | 鸿蒙专项测试 daemonize 用例偶发 `FAIL: daemonize/--logfile: pid file '' is not a pid`（W3 第 4 轮 conan create 命中一次） | 上游 `main()` 先 `fopen(pidfilename,"w")`（**空文件**）→ 再 `daemon()`（父进程在此退出）→ 子进程才 `fprintf` 写入 pid；测试只等"文件存在"就立即读取，与子进程写盘竞态，可能读到空串 | 改为等"文件内容是非零数字"（`wait_for(pid_written)`）再取 pid；前台用例本就按 `内容 == Popen pid` 判定，天然免疫该竞态 | 连续 5 次单跑 + 修复后 W3 `conan create` 均 6/6 通过 |

## 源码修改

**源码本体未改**（`inoticoming.c` / `closeallfds.c` 一字未动，无平台宏、无 stub、无功能裁剪）。

**唯一变更 = `patches/0001-configure.patch`**：把发行包自带 `configure` 里 autoconf
建临时目录的 `(umask 077 && …)` 放宽为 `(umask 022 && …)`（2 处，+2/-2），
修复 E011（HMDFS 上 0700+setgid 临时目录连创建者都不可写 → config.status 写
`subs1.awk` 报 Permission denied）。

为什么用补丁而不是配方内联替换：
`apply_conandata_patches()` 作用于 `source_folder`，与 `basic_layout` 的
`build_folder`（`build-<build_type>`）取值无关；内联替换若只扫 `self.build_folder`
会因 `os.path.isfile` 守卫**静默跳过**，症状与"完全没修"一模一样。
补丁由 `ohc-run.py refresh-patch --auto` 生成（tracker 模式按哈希变化收录 `configure`）。

## 依赖版本

无。编译期/运行期依赖只有 OHOS libc（提供 `sys/inotify.h` 与 inotify 系统调用）。

## 验证结果

```bash
# 上游测试入口（0 用例，见 reports/test-report.md 第一节）
$ make check ; echo $?
0

# 手工编译产物
$ ./inoticoming --version
inoticoming 0.2.3

# 真机功能实测（节选）
Will call action /…/action.sh for: a.txt     # IN_CLOSE_WRITE
Will call action /…/action.sh for: b.txt     # IN_MOVED_TO（mv 进目录）
SIGTERM → 退出码 0

# 配方验证（conan create + G0-G4 + L2/L4/L5）
$ python3 scripts/ohc-run.py conan-verify inoticoming 0.2.3
✅ 配方验证通过: inoticoming 0.2.3     # reports/conan-verify-report.md Verdict=PASS

# W3 本地 CI 模拟（与 CI 同口径：setup.sh + build_and_test.sh）
$ python3 scripts/ohc-run.py finish inoticoming 0.2.3 built
  JC: 检查模式 prdiff (14 个文件) → Junk Files: 0, JC_RESULT=pass（JC6 涉及软件数 1，合规）
  KC_RESULT=pass
  L0_RESULT=pass / L1_RESULT=pass（上游测试 + test_package 均已执行，L1c 上游 make check 已在 build 阶段执行）
  L2_RESULT=pass（--version OK）/ L4_RESULT=pass（patches clean）/ L5_RESULT=pass（bin/ 有内容）
  Pass rate: 100.0% (1/1)
  .ci-result.json: exit_code=0, log_sha256=59f11451…（= sha256(reports/w3-local-ci.log)，实测一致；timestamp 2026-09-23T12:48:48）

# test_package（conan create 内自动运行）
RESULT: 6 passed, 0 failed    # test_inoticoming.py（消费者）
RESULT: 6 passed, 0 failed    # test_ohos_inoticoming.py（鸿蒙专项）
HMBS_TEST_PACKAGE_RESULT={"discovered": 12, "passedCount": 12, "passed": true}
HMBS_UPSTREAM_TEST_RESULT={"status": "no_tests", ...}
```

> W3 的 prdiff 模式：本机 `origin/main` 是陈旧个人 fork（落后规范 main 3234 个提交），
> 若走 incremental 模式会把上游提交里新增的 1735 个包误算进本次 PR；
> 因此按 CI 的真实口径提供 `<repo>/pr.diff`（只含本次待提交的 12 个新增文件 =
> 12 个包文件），使 JC 只审本 PR 的文件
> （JC1/JC5 未登记项、JC6 原子性均据此判定）。

日志路径：`reports/step2-configure.log`、`reports/step2-make.log`、
`reports/step2-make-check.log`、`reports/step2-make-check-dryrun.log`、
`reports/step2-make-install.log`、`reports/conan-create.log`、
`reports/w3-local-ci.log`、`reports/conan-verify-report.md`、`reports/test-report.md`
（`reports/` 依仓库 `.gitignore` 约定不入版本控制；`/storage/Users/currentUser/tmp/inoticoming-consumer-test/consumer.log`、
`…/inoticoming-ohos-test/ohos.log` 为 conan create 内的测试原始日志）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/inoticoming` | 守护进程主程序（ELF64 AArch64 PIE，PT_INTERP=`/lib/ld-musl-aarch64.so.1`） |
| `share/man/man1/inoticoming.1` | 上游 man 页 |
| `licenses/COPYING` | GPL-2 许可证文本 |

## 注意事项

- **`--initialsearch` 依赖 readdir 的 `d_type`**：上游用 `ent->d_type != DT_REG` 跳过目录项。
  本机各文件系统实测 `d_type` 有值（无 `DT_UNKNOWN`），预存文件可正常处理；若换到返回
  `DT_UNKNOWN` 的文件系统需留意（鸿蒙专项测试用例 3 覆盖该契约）。
- **OHOS 无 syslogd**：守护进程未带 `--logfile` 时自身日志走 `vsyslog`，无 syslogd 会丢失；
  生产使用应显式给 `--logfile`（`daemon()` 会 `chdir("/")`，`--logfile`/`--pid-file`/动作/参数
  必须用绝对路径）。
- **动作程序找不到时静默退出**：上游 `doaction()` 在 `execvp` 失败时不报错、子进程以 0 退出，
  因此动作是否真的执行必须以动作自身的副作用（本仓库用 marker 文件）判定，`--foreground`
  下仅 "Will call action …" 一行日志不代表执行成功。test_package 因此断言 marker 内容。
- **未做 ELF 签名**：与 `detachtty`/`inotify-tools`/`cachefilesd-inotify`/`cvs-mailcommit`
  等近期可执行包一致，签名由 CI 的 `ci/artifacts/sign.sh`（GPG，非阻塞）负责；
  实测未签名的产物在本机可直接运行（`--version`/守护进程均正常）。

## 上游测试申报表（R51）

| 项 | 值 |
|---|---|
| 上游测试目录数 | 0（tar 包 26 个条目中无 `tests/`、`test/`） |
| ctest/automake/pytest 注册用例数 | 0（`Makefile.am` 无 `TESTS`/`check_PROGRAMS`；`make -n check` 只展开编译规则） |
| 可运行环境实测 | ✅ 已实测 `make check`：手工阶段退出码 0 且无输出（日志 `reports/step2-make-check.log`、`reports/step2-make-check-dryrun.log`）；配方阶段由 `build()` 调用并在 `conan create` 内执行（`RUN: make check -j1`，见 `reports/w3-local-ci.log:244` 与 `.ci_logs/conan_build_inoticoming_0.2.3.log`） |
| PR 回填实测值 | 上游 N=0 / N′=0（0 个用例可运行，无失败、无跳过）；适配方 12/12 通过（`reports/test-report.md` 第二节） |
---

## 对话记录

### 对话 #1 [2026-09-23]

**用户**：`inoticoming 0.2.3 https://sources.debian.org/src/inoticoming 目标库适配.txt 根据这里的知识完成我给的目标库的适配`

**Agent（本轮）**：
1. W0/W0b：确认本包无第三方依赖（`preflight_check.sh inoticoming/0.2.3` → 无依赖需检查）；仓库无
   inoticoming 历史归档；核验同类平台知识 `archives/i/inotify-tools/4.25.9.0`（OHOS 支持 inotify，
   不支持 fanotify）。
2. W1：`git fetch upstream main` 后把本地 `main` 快进到规范 main `59eaed1f64`（本地 `origin/main`
   为陈旧个人 fork，落后 3234 个提交），从 main 切出 `feat/inoticoming-0.2.3`。
3. init-build + lang-preflight（task=cpp / detected=c，c↔cpp 兼容族通过）+ 源码核验（26 个条目、
   无 tests/、无 TESTS 注册）。
4. 模式 B 手工构建：命中 E011（HMDFS umask 077 → `config.status` 报 "could not setup config files
   machinery"）；第一版修丁落错目录（只扫 `build_folder`）导致**原错误一字不差复现**，改为
   `patches/0001-configure.patch` 作用于 source 树后通过。
5. 固化：conanfile.py（autotools + application + commands.json）+ conandata.yml + test_package
   （6 消费者用例 + **6 项鸿蒙专项测试**：OHOS ELF/装载器身份、inotify 内核 ABI、`--initialsearch`
   的 readdir d_type、`--pid-file`、`--chdir`、无 syslogd 的 daemon+`--logfile`）。
6. 验证：`conan-verify` PASS（G0-G4/L2/L4/L5）→ `finish`（W3 `build_and_test.sh` JC/KC/L0-L5 全过、
   `conan create` + test_package 12/12、`.ci-result.json` exit_code=0）；W5 知识完整性通过。
7. W4：按 `templates/audit-prompt.md` 派发独立审计子任务；首轮 verdict=fail（P1：README.md 仍描述
   旧的"配方内联替换"口径，与实装的补丁机制矛盾；P3：鸿蒙专项测试未按目标 OS 门控）→ 已修复
   （README 改为补丁口径；test_package 仅在 OHOS 目标启动鸿蒙专项测试，其它目标如实报 skipped）。

**状态**: built（本地 conan create / W3 全绿，未上传制品仓；按任务要求在 commit/push/PR 前停下等待确认）

状态: built
---

**编译结束**: 2026-09-23 12:47
**最终状态**: built
