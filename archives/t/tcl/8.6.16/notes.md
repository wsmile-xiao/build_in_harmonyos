# tcl 8.6.16 适配 notes

## 上游测试验证记录（2026-08-05，作者自评留痕）

### 本地验证环境
- 设备：HarmonyOS PC arm64
- 工具链：clang 19.1.0+libc++（鸿蒙原生）
- tcl 源码：8.6.16 上游 release tarball

### 验证方式
执行 `make test-tcl`（ERROR_ON_FAILURES=1 驱动 tcltest 遇失败 exit 1），解析 upstream_test.log 汇总行：

| 项目 | 值 |
|------|-----|
| 检测文件数 | 完整覆盖 |
| 总用例 | 46782 |
| 通过 | 46762 |
| 失败 | 20 |
| 通过率 | **99.96%** |
| 失败用例性质 | **均为环境限制**（/tmp 只读、/ 目录权限受限、HMDFS xattr 缺失），非功能回归 |

### CI 复跑预期
CI 环境（可写 /tmp + 完整权限）应能跑全绿，本地 HMDFS 限制导致的 20 个失败用例在 CI 不会出现。

### 配方对应实现
conanfile.py 第 77-115 行：`make test-tcl` 驱动 + upstream_test.log 解析 + `raise ConanException`（规则 5：任一失败即构建失败，commit `d0ea030ec`）。

## AI review 修复轨迹

| commit | 修复 |
|--------|------|
| `8d91c5e09` | manifest.yaml system 字段 makefile→autotools |
| `5cf12025c` | 规则5测试改非阻塞模式（warning 替代 raise） |
| `d0ea030ec` | 规则5改回 raise ConanException（评审要求：任一失败即构建失败） |
|本轮| P2: test.c 第二次 Tcl_Eval 补 concat_result 内容验证；P3: 移 TARGET_SO 未用段 |

## Issue #2149 dependency adaptation (2026-08-14)

### W0

`zlib/1.3.1` is published in the `ohpcd` remote for OHOS 6.0 / armv8 as
package ID `6b129b068851896169fae42d399fa922d239ce8a`. No additional dependency
split is required.

### Front adaptation

- Package upstream's installed `bin/tclsh8.6` and fail when it is absent.
- Sign `tclsh8.6` with the OHOS runner's LLVM objcopy and binary signing tool.
- Export `PATH`, `TCL_ROOT`, `TCL_LIBRARY`, and the package library path through
  Conan build and run environments so downstream `tool_requires` can execute
  Tcl without interactive-shell setup.
- Strengthen the C API consumer to seven assertions and provide a seven-assertion
  Tcl interpreter consumer launched by command name.

### Local validation

Source hash verification, patch dry run, Python/YAML parsing, Conan inspect,
isolated Conan export, and Git whitespace checks passed. A Git-bundled Tcl
8.6.18 ran a version-substituted in-memory copy of the new Tcl test with 5/5
assertions passing. This does not claim execution of the packaged OHOS binary.

No real-device slot was used. The next single-package commands are:

```sh
CI_PACKAGES="archives/t/tcl/8.6.16" zsh ci/conan/build_and_test.sh
/path/to/run-ohos-shadow-ci.sh archives/t/tcl/8.6.16
```

### Shadow CI retry 1

The committed snapshot at `a706bee47b707264430da8e810ea5e95eb863c9e`
passed input, environment, and setup verification on the HarmonyOS device. Tcl's
core shared library and `tclsh` linked, but `make` stopped in
`configure-packages` because HMDFS rejected direct execution of
`pkgs/itcl4.3.2/configure` with Error 126 (`Permission denied`). The recipe now
patches the generated Makefile to invoke every package configure script through
`bash`, following the documented HMDFS noexec workaround. The failed run is
preserved at
`/storage/Users/currentUser/ohpc-ci-shadow/runs/a706bee47b70-20260814T062615Z-run-3843`;
its build log SHA-256 is
`c3aecfccd43e523c93e977b6209f747295a55bf1966fbf47163c4e2214477a95`.

### Shadow CI retry 2

The committed snapshot at `3824af370713b4d86626d1d7edf624bf1980fdae`
passed preflight and setup. The explicit Bash invocation fixed the original
failure: all bundled package configure steps and their builds completed, then
the full `make test-tcl` suite ran 46,730 cases. It reported 44 failures before
the recipe's environment filter. Every newly unclassified failure was rooted
in HMDFS denying symbolic-link creation with `POSIX EACCES`; the later
`filename-11.*` and `filename-14.*` mismatches were cascades from the leftover
`globTest/nonexistent` directory created by the failed symlink test.

The common-issues guide documents incomplete or restricted symlink support on
the device filesystem. The environment allowlist therefore adds only the
observed `fCmd-28.*` symlink family and the exact cascading filename cases;
unknown failures remain fatal. The failed run is preserved at
`/storage/Users/currentUser/ohpc-ci-shadow/runs/3824af370713-20260814T064620Z-run-22165`;
its build log SHA-256 is
`fea7d5da148fd064868e46d9c69e7b4ad8ed7894a43482d112e187abae395938`.

### Shadow CI retry 3

The committed snapshot at `55ebf1b6f7f02acc0007b582d5cd648768f1e43f`
completed the automated runner with status `pass`. Both the six-assertion C API
consumer and five-assertion `tclsh8.6` consumer passed, as did the destructive
negative test. The preserved run is
`/storage/Users/currentUser/ohpc-ci-shadow/runs/55ebf1b6f7f0-20260814T070613Z-run-50072`;
its build log SHA-256 is
`034ee84bfec1c821d2939f06751edf26d322440fcdd212986c54456d1e0bd260`.

Manual review found two quality gaps despite the runner's zero exit status.
First, `libtcl8.6.so` had no `DT_SONAME`, producing
`L5_RESULT=fail: soname_gate_failed`. Second, `thread.test` crashed after
`thread-5.2`; the existing parser saw only named test failures and did not
reject the `Test file error: child killed: segmentation violation` marker.

A locked single-test reproduction confirmed that `thread-5.2` alone crashes
when the OHOS pthread implementation is asked to join a detached thread. A
second locked diagnostic skipped only that platform probe and ran the complete
remaining `thread.test`: 52 total, 49 passed, 3 skipped, 0 failed. Its audit
directory is
`/storage/Users/currentUser/ohos-test-runs/codex-tcl-issue-2149-thread-skip52-diagnostic-20260814-152945-32769`.
The recipe now skips only `thread-5.2` on OHOS, makes every other test-file
error fatal, and adds `DT_SONAME=libtcl8.6.so` through the generated Makefile's
shared-library linker definition.

### Shadow CI retry 4

The committed snapshot at `f5c89cb7e36f8c9a617b2ad1ab029dd901b2f0ce`
confirmed the SONAME flag in the real shared-library link and completed all
46,782 test accounting entries without a `thread.test` crash. The new hard
test-file gate then correctly stopped the build on the remaining marker:
`Test file error: couldn't open "/tmp/touch.me": read-only file system`.
The failed run is preserved at
`/storage/Users/currentUser/ohpc-ci-shadow/runs/f5c89cb7e36f-20260814T073959Z-run-42640`;
its build log SHA-256 is
`ee3e9fe87b5b08487725bedb59a40f6db6f8d8e98f006eac8d63c0352bf968b7`.

This error is a top-level fixture in upstream `cmdAH.test`, not an individual
test result; leaving it in place prevents later cmdAH cases from running. The
second source patch now attempts the fixture's preferred `/tmp` location and
falls back to its existing build-directory branch when `/tmp` is not writable.

### Shadow CI retry 5

Snapshot `406d420d6b8cf46638738eb0613623aa878706c5` passed preflight but
stopped before compilation because Conan's patch engine requires the exact
source line and does not accept Git's automatic two-line offset. The failed run
is preserved at
`/storage/Users/currentUser/ohpc-ci-shadow/runs/406d420d6b8c-20260814T080321Z-run-14299`;
its build log SHA-256 is
`d4699183d45093a3e6a01f04bf237f5cc2c36bd586d1f34a868af7a0b8b0a922`.
The patch hunk now starts at the release tar's exact line 1013; its context and
behavior are unchanged.

### Shadow CI retry 6

Snapshot `830d372e7ed8d949566e9266fd8c0fa07bf2b49d` applied all patches and
ran 47,105 upstream cases with `file_errors=0`. Five later cmdAH cases were
newly visible after the top-level fixture stopped aborting the file. Two still
hard-coded `/tmp`; patch 0003 moves those fixtures to a writable path when
needed. The remaining exact cases are an ACL mode-mask difference
(`cmdAH-28.5`) and the already-proven HMDFS symlink EACCES
(`cmdAH-29.4`, `cmdAH-29.4.1`). The failed run is preserved at
`/storage/Users/currentUser/ohpc-ci-shadow/runs/830d372e7ed8-20260814T081220Z-run-23532`;
its build log SHA-256 is
`735738c418a86618d9f8076d287cfc2dbc4825eb0c6b7617c568c2cf8019c4cb`.

### Shadow CI retry 7

Snapshot `3938123c434667e467664487fbcb7cd3ced6e663` applied all three
patches and again completed 47,105 upstream cases with `file_errors=0`.
`cmdAH-24.5` passed after the writable-path fallback. `cmdAH-25.2.1`
also ran to completion in the writable HMDFS build directory, where
`file owned` returned `0` instead of the Unix expectation `1`; classify
that single case as an exact HMDFS ownership-mapping difference. The
failed run is preserved at
`/storage/Users/currentUser/ohpc-ci-shadow/runs/3938123c4346-20260814T091332Z-run-18509`;
its build log SHA-256 is
`78223fd85158f7bdef2c5cd6c21eba1cd2676d8d7b3df7765ab946bf005a3c1c`.

### Downstream Redis dependency validation

Redis 6.2 shadow CI run
`/storage/Users/currentUser/ohpc-ci-shadow/runs/f14a117dfb92-20260814T151813Z-redis-tcl-run-1139`
proved that the Tcl package could launch the upstream integration suite, but
the suite stopped after 19 of 63 groups when `clock format` required
`msgcat 1.6`. The package contained the versioned `lib/tcl8.6` runtime and its
message catalogs but not the Tcl Modules directory that registers msgcat.
The Redis build log SHA-256 is
`72b1c350cb490068af4f35c71cf737bf04f03bdf096598a8c4c30a5cce89589d`.

The validated Tcl staging tree contains
`lib/tcl8/8.5/msgcat-1.6.1.tm`; it was omitted because `package()` copied only
`lib/tcl8.6`. The recipe now packages the complete `lib/tcl8` module tree.
The interpreter consumer requires `msgcat 1.6` and formats the Unix epoch so
future packages cannot pass while `clock.tcl` is incomplete.

### Shadow CI Tcl Modules fix

Snapshot `fdc79d749dda51037585dc1be1575ee8df3a5cd6` completed the Tcl
single-package runner with status `pass`. The upstream suite accounted for
47,105 cases with `file_errors=0`; all 49 failures matched the existing exact
OHOS filesystem-environment classification. The C API consumer, destructive
negative test, and the expanded interpreter consumer passed. The latter
reported `PASS msgcat package: 1` and
`PASS clock format: 1970-01-01` from the packaged Tcl runtime.

The preserved run is
`/storage/Users/currentUser/ohpc-ci-shadow/runs/fdc79d749dda-20260814T154117Z-tcl-msgcat-run-14914`;
its build log SHA-256 is
`da46e40458b1ac882bb9189d4f18370069ea869dd384a0c1919c3741dedf6f70`.
The exported cache for Redis validation has SHA-256
`3b742a313f08c8081898f419f97fa75cd8693c1d5e1c06056b9d95fb93972afe`.

### Focused current-head consumer recheck

Snapshot `2d8bba22c0a331fe96a9566c127ec0287e673d39` strengthened the C
consumer by requiring the `expr 2 + 3` result to equal `5`, rather than only
checking `Tcl_Eval`'s return code. The updated source was compiled on the
HarmonyOS device with the same OHOS Clang toolchain and package produced by
the full passing run above. All seven C assertions passed, including:

```text
expr 2 + 3 = 5
Smoke test PASSED.
```

The isolated evidence directory is
`/storage/Users/currentUser/ohpc-ci-shadow/current-head-tests/2d8bba22c0`.
The uploaded `test.c` SHA-256 is
