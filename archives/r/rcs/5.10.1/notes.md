# rcs 5.10.1 adaptation notes

## Scope

- Target package: `rcs/5.10.1`（GNU RCS，修订版本控制系统工具集）
- Run: `rcs-5.10.1`（base `9496e9c8f198e1d2af48d62f370b70d592682db9`）
- 下游诉求：姊妹 run `changetrack-4.7` 的上游测试门禁需要 RCS 套件（`ci`/`co`/`rcsdiff`/`rlog`），本包交付后经 conan `requires()` 引入。

## Version confirmation

- 上游：GNU rcs 5.10.1（https://ftp.gnu.org/gnu/rcs/，官方 `.tar.lz` 需 lzip，设备无 lzip）。
- 采用内容等价的 Debian orig tarball：
  `https://deb.debian.org/debian/pool/main/r/rcs/rcs_5.10.1.orig.tar.xz`
  SHA256 `37b5b39d2395ae21eb246d2ebf5ee242d54a72d11e8f8a3a4d818368e45a6bff`，
  与 `rcs_5.10.1-4.dsc` 权威校验值一致，并已在设备上下载实测比对一致。
- License：GPL-3.0-or-later。
- 构建系统：标准 autotools，tarball 自带 configure、预生成 Makefile.in、内嵌 gnulib（`lib/`），无需 bootstrap；`doc/rcs.info` 预构建，构建全程 `MAKEINFO=true`。

## Build shape

- 产物：`bin/rcs`（多调用真实二进制）+ `bin/ident`、`bin/merge`（独立二进制）+ 6 个 `#!/bin/sh` wrapper（`ci`/`co`/`rcsclean`/`rcsdiff`/`rcsmerge`/`rlog`，由 `src/sub.TEMPLATE` 生成，`exec "$d"rcs SUB "$@"`）。设备实测 `/bin/sh` shebang 可执行（E165）。
- configure 要点：`--disable-suid`（非 setuid 场景，同时使 `getusername` 走 env 优先路径）；mmap 默认开启（HMDFS 异常时可加 `--disable-mmap`，本轮未启用）；`DIFF` 自动探测到 GNU diffutils 3.10（`/data/service/hnp/bin/diff`）。
- configure 无条件要求 `ed`（`RCS_ABSOLUTE_PROGRAM(ED)`），故 `tool_requires("ed/1.20")`；运行期仅在 diff3 不完全兼容时用于 `rcsmerge` 回退，设备 diff3 探测为 sane，不影响实际运行。
- 与 m4 1.4.19 同款 OHOS 构建路径：显式 `--build/--host=aarch64-unknown-linux-ohos`、`CONFIG_SHELL=/data/service/hnp/bin/bash`、`AutotoolsToolchain.environment()` 注入编译器变量。

## Patches（6 个，全部最小化、可解释）

1. `0001-recognize-ohos-triplet-config-guess.patch` — config.guess（2022-01-09）识别 `__OHOS__` 与 `HarmonyOS` uname，输出 `aarch64-unknown-linux-ohos`（E007 先例同款，适配 rcs 版本的 musl 探测结构）。
2. `0002-recognize-ohos-triplet-config-sub.patch` — config.sub（2021-12-25 旧式结构）接受 `ohos*` OS 与 `linux-ohos*` kernel-os 组合（E072）。
3. `0003-use-readable-configure-tempdirs.patch` — configure 中 4 处 `umask 077` → `022`（E011：HMDFS 上 0700 临时目录不可回读，含 gettext gt 块）。
4. `0004-treat-empty-login-as-unset.patch` — `src/b-excwho.c getusername()`：设备 `getlogin_r()` 返回成功但空串、`LOGNAME` 环境变量为空串、且 `/etc/passwd` 无该 uid 条目，原逻辑会以空用户名继续，随后所有 `ci`/`co` 因 `invalid identifier '`' 中止。补丁使 JAM 宏拒绝空串，回退链继续（env → getlogin → passwd），与上游 `PFATAL ("Who are you?  Please setenv LOGNAME.")` 的语义一致。
5. `0005-honor-tmpdir-in-tmpfile.patch` — `src/rcs.c`：设备 `/tmp` 只读，`tmpfile(3)` 恒失败（`rcs -o` 与锁破坏邮件路径）。新增 `dir_tmpfile()`：mkstemp 于 `$TMPDIR`（测试套件自身会设置），保持 tmpfile 语义（打开即 unlink）。
6. `0006-fallback-tempdir-to-cwd.patch` — `src/b-feph.c jam_sff()`：`maketemp` 在系统临时目录 mkstemp 失败时回退 cwd，保证 `TMPDIR` 未设置时 `co`/`ci`/`rcsdiff`/`merge` 仍可用（t805 显式 `unset TMPDIR` 压测此路径）。

## Upstream test suite（真实运行）

- 入口：`make check`；上游共 63 个纯 POSIX shell 测试（`t010`–`t999`），无需 perl/Expect/ed；上游 `known-failures.in` 中 5.10.1 清单为空（无官方已知失败）。
- 设备实测（VPATH 构建，`LOGNAME=builder`，`make -j1 check MAKEINFO=true SHELL=/data/service/hnp/bin/bash`）：
  **60 PASS / 3 FAIL**，失败项逐个分析：
  - `t790`（rcsclean 只读 cwd 报错路径）：测试以 `chmod u-r .` 模拟不可读目录——HMDFS 忽略 `chmod(2)`，目录始终可读，rcsclean 成功 → 平台固有限制。
  - `t900`（b.make 全量回归）：`ci -u`/`co` 依赖"签出产生只读工作文件"约定——HMDFS 上 `chmod` 无效，工作文件恒为 0640（可写），后续 `co -l` 报 `writable b exists` 中止 → 平台固有限制。
  - `t999`（RCS 文件名解析终测）：`for l in '' '-l'` 循环中 `co`（无锁、只读产物）之后再 `co -l`，同样因只读位不可表达而中止 → 平台固有限制。
  - 三者根因相同：HMDFS 的 chmod(2) 为 no-op（设备实测 `chmod 444` 后仍为 0640），RCS "只读工作文件"安全模型无法表达。recipe 的 `build()` 以白名单容忍且仅容忍这三项：出现任何其他失败或不足 60 通过即构建失败。
- 修复链实证：初始裸跑 40/63 → 补丁 0004/0005（登录名 + tmpfile）后 59/63 → 补丁 0006（mkstemp cwd 回退，t805 `unset TMPDIR` 压测）后 60/63。
- 每轮 `make check` 日志留存于 conan build 目录 `upstream-check.log`（CI L1c 可见 `make check` 执行痕迹）。

## conan 上下文的两个设备侧关键点（recipe 内已固化）

- **PWD 一致性**：bash 仅在 `PWD` 环境变量与实际 cwd 不一致时才调用 `getcwd(3)`，而 conan（python `os.chdir` + posix_spawn）派生的进程在 HMDFS 上 `getcwd(3)` 返回 ENOTSUP（`shell-init: getcwd ... Not supported`、每作业 `job-working-directory` 噪声污染测试输出）。recipe 通过 `os.environ["PWD"]=build_folder` 与在 `tests/` 叶子目录内以 `PWD=<tests>` 前缀运行 `make check`（= check-am，含 `check_PROGRAMS` 构建）规避；实测修复前 50 PASS/10 FAIL/3 SKIP，修复后 60 PASS/3 FAIL。
- **CONFIG_SHELL**：ohos-aarch64 profile 的 buildenv 固定 `CONFIG_SHELL=bash`，但 configure 由 `/bin/sh`（mksh）运行即可；若 re-exec 到 bash 会因上述 getcwd 问题在 autoconf 初始化即失败（`working directory cannot be determined`），故 recipe 在 configure 调用前缀 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh`，测试阶段才用 `SHELL=<bash>`。

## Test package

- 9 个命令逐一 `--version` 断言；
- 真实 `,v` 仓库往返：`ci -i`（含 `-t` 描述文件）→ `co -l` → 第二次 `ci` → `co -r1.1` 旧版内容断言 → `rcsdiff -r1.1 -r1.2` 差异断言 → `rlog` 修订列表断言 → `co -kvl` + `ident` 关键字断言 → `rcsclean -n` 可清理断言 → `rcsmerge -r1.1 -r1.2` 折叠断言；
- 测试内固定 `LOGNAME/USER=rcs-tester`（设备默认空 LOGNAME 会使 ci/co 中止）。

## Device validation log

- 手动 VPATH 构建 + make check：`/storage/Users/currentUser/tmp/oh-device-porting-v2/rcs-5.10.1/build-manual/`（check.log、tNNN.d 残留）。
- `getlogin_r`/`getpwuid` 行为验证：`tl.c` 一段式探针（getlogin_r=0 buf=[] len=0；pw_name 无条目）。
- HMDFS chmod 探针：`chmod 444` 后 `stat` 仍 640。

## Risks / known gaps

- 设备终端直接使用本包时需 `export LOGNAME=<非空名>`，否则 `ci`/`co`（涉及锁）报 "no password entry"；只读查询（`rlog`/`ident`/`co` 只读签出）不受影响。
- 依赖系统 PATH 上的 `diff`（`rcsdiff` 通过编译期烘焙的绝对路径调用 `/data/service/hnp/bin/diff`）。
- `t790`/`t900`/`t999` 在任何 HMDFS 文件系统上均无法通过，非本包缺陷。
