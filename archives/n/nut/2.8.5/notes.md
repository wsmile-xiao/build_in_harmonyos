# NUT 2.8.5 HarmonyOS adaptation notes

## Scope

This branch prepares the first Conan package for Network UPS Tools 2.8.5.
The selected build is the dependency-free software-only core:

- NUT clients and daemons
- `dummy-ups` and `upsdrvctl`
- static NUT libraries and development headers
- no USB, serial, SNMP, SSL, CGI, Python, systemd, or scanner integration

The optional hardware and protocol integrations should be adapted as separate
dependency packages before they are enabled in a follow-up NUT revision.

## Source

Official release archive:

`https://networkupstools.org/source/2.8/nut-2.8.5.tar.gz`

SHA256:

`18bf32e59eb764b13da3c4fa70384926d7fa584cb31d2fe7f137a570633eeec1`

The release archive already contains `configure`, `config.guess`,
`config.sub`, and the generated `Makefile.in` files.

## Discoveries

- ✅ `config.guess` has no HarmonyOS branch. The patch adds
   `aarch64-unknown-linux-ohos` detection from `uname`.
- ✅ `config.sub` rejects the `linux-ohos` kernel/OS combination. The patch adds
   it to the accepted triplet and OS validation lists.
- ✅ `config.guess` keeps `umask 077` for its secure paths and uses `022` only
   for its final insecure fallback. The generated `configure` selects `022`
   only for `linux-ohos` `config.status` scratch directories; other hosts
   retain the upstream `077` mode.
- ✅ `build()` places `TMPDIR` below `$HOME/.tmp` and provides
   `CONFIG_SHELL=/system/bin/sh` for OHOS.
- ✅ `make` and `make check` use `-j1` because the device filesystem can reject
   parallel make jobserver FIFO operations.
- ✅ HMDFS can reject direct execution of unpacked `configure` even when the
   source archive contains executable bits and `chmod` is attempted. OHOS
   builds invoke it explicitly through `/system/bin/sh`.
- ✅ The shared OHOS profile provides clang/clang++ by absolute path but does
   not add `/data/service/hnp/bin` to `PATH`; configure needs that directory
   plus `llvm-ar` and `llvm-ranlib` for archive detection.
- ✅ The release does not assume that `getpass` is available. `configure`
   detects `getpass` and `getpassphrase`; when neither is provided, `proto.h`
   supplies a portable `/dev/tty` fallback with termios support when the
   corresponding headers are detected, without a platform macro branch.
- ✅ OHOS/HMDFS rejects the generated `tests/hidparser.c` symlink. The test
   rule copies the source file on `linux-ohos` on every recipe invocation, so
   an incremental build cannot retain stale copied contents; other platforms
   retain the original symlink rule.
- ✅ `configure` selects `LN_S=cp -pR` on OHOS, but the `docs/man` preparation
   rule hardcodes `ln -fs`; the generated and source makefiles now use
   `$(LN_S)` so documentation preparation also works without symlink support.
- ✅ The top-level `docs` preparation rule had the same hardcoded `ln -fs`
   operation. Its generated and source makefiles now also use `$(LN_S)` on
   OHOS.
- ✅ The `data` driver-list validation hooks directly executed
   `driver-list-format.sh`; they now invoke it through `$(SHELL)` so
   `make check` works on OHOS filesystems that reject direct script execution.

## Local status

The current host is Windows and does not expose the OHOS clang/make toolchain
or a device profile. Recipe syntax, source metadata, patch declarations,
archive structure, and patch application were checked locally. The complete
OHOS package build and smoke validation were completed by Shadow CI on the
target device.

## Shadow-CI handoff

The final standard runner completed on 2026-09-12 after waiting 76 seconds for
the device-global heavy lock:

`codex-2.8.5-nut-2.8.5-20260911-conan-20260911-233949-48628`

The run returned exit code `0`. Read the retained logs with:

```sh
RUN="$HOME/ohos-test-runs/codex-2.8.5-nut-2.8.5-20260911-conan-20260911-233949-48628"
cat "$RUN/logs/exit-code.txt"
cat "$RUN/logs/stdout.log"
tail -n 120 "$HOME/ohos-users/codex/nut-2.8.5-20260911/repo/build_in_harmonyos/.ci_logs/conan_build_nut_2.8.5.log"
```

The final run verified:

- All eight NUT portability patches applied and the package was created.
- `make -j1` and `make check -j1` completed successfully.
- The generated default Automake test list ran 4 tests:
  `nutlogtest`, `nuttimetest`, `nutbooltest`, and `driver_methods_utest`;
  all 4 passed, with 0 failures and 0 errors.
- The source archive also ships optional USB (`getvaluetest`,
  `getexponenttest-belkin-hid`), GPIO (`gpiotest`), and CppUnit
  (`cppunittest`) tests. The NUT Integration Testing suite
  (`tests/NIT/nit.sh`) is also present. This profile intentionally disables
  those optional suites (`--with-usb=no`, `--with-gpio=no`,
  `--enable-cppunit=no`, `--disable-check-NIT`); the NIT `make check` entry
  is recorded as `NO-OP`, so they are not part of the 4/4 executed-test rate.
- The package contained `bin/upsc` and `bin/upsd`; the revised `test_package`
  checks `upsc -V`, `upsc -h`, and `upsd --version`. AtomGit CI #44740 passed
  all eight consumer assertions.
- The package reference was
  `nut/2.8.5#d39703f7c344bc45beb2f39d0d43089a:6b129b068851896169fae42d399fa922d239ce8a#e3e486d055572a7f2263fdea09c8ab9e`.
- Shadow CI reported `L0=pass`, `L1=pass`, `L2=pass`, `L5=pass`.

`L4` was reported as `warn` because its scanner detected the intentional
termios-based `getpass` compatibility code in
`0004-upsrw-ohos-getpass.patch`; this did not fail the run. The non-blocking
warnings for `upslog`, `upssched`, and `upssched-cmd` also did not affect the
overall result. Device toybox messages from `gitlog2version.sh`, `touch`, and
`id` were non-fatal and the generated package and tests completed.

## AI-review follow-up

The first review-fix CI run was AtomGit build `44728`. It correctly reached
the OHOS configure stage, but failed at `config.status` while creating
`conf*/subs1.awk` with `Permission denied`. Restoring `umask 077` everywhere
was therefore too strict for the HMDFS build scratch directory. The follow-up
keeps secure `077` behavior for `config.guess` and non-OHOS configure runs,
while selecting `022` only for `linux-ohos` `config.status` scratch creation.
The current PR head then passed AtomGit CI build `44802`: all workflow steps
completed, Conan `test_package` passed, and L0/L1 passed. The cleanup step
reported only CI-infrastructure warnings about `buildbot.tac` and HOME path
normalization; they did not affect the package result and are outside this
library PR's permitted scope. The branch is recorded as `built`; the CI
summary does not publish a separate L4 result.

## 路径 B 可复用知识草稿

本库补充了路径 B 候选草稿：

`knowledge/drafts/DRAFT-nut-autotools-ohos-upstream-check-chain.{kv,md}`

草稿的新增点不是重复申报单独的 config.guess、HMDFS umask、软链接或
getpass 修复，而是记录旧式 Autotools 包在 OHOS 上从生成规则审计到
`make check`、HNP 工具 PATH、Conan 实际包布局和消费者断言的完整闭环。
它保留了 run `40813`、`50315`、`43803`、`6990`、`38515`、`21715`
到最终 run `48628` 的失败收敛证据，可迁移到带递归上游测试的同类库。

本次适配按“路径 A + 路径 B 候选”整理；是否最终认定为 B 类难度库及
是否计分，以知识库主编和赛事评审结果为准。

## 最终状态

前置适配和标准 Shadow CI 已完成，当前状态为 `built`。本轮一库一分支
工作区中的 NUT 修改已经通过真机上的 Conan 构建、上游测试和
`test_package`。未单独启动真实 UPS 服务或接入硬件驱动；本轮范围仅启用
软件核心和 `dummy-ups`，后续硬件/协议集成仍应拆分为独立依赖和变更。
