# sisl 4.6.0 adaptation notes

## Task and source
- Registry task: 10653; agent: 主理-4.
- Worktree: `feat/sisl-4.6.0`, base `origin/main` at `48d9cee6844d0fca1f25e86c2df1293b904855d8`.
- Upstream: https://github.com/SINTEF-Geometry/SISL, tag `SISL-4.6.0`.
- Source URL: https://codeload.github.com/SINTEF-Geometry/SISL/tar.gz/refs/tags/SISL-4.6.0
- SHA-256: `b207fe6b4b20775e3064168633256fddd475ff98573408f6f5088a938c086f86`
- Conan `get()` uses explicit filename `SISL-SISL-4.6.0.tar.gz` because the direct codeload URL has no archive suffix.
- License: AGPL-3.0-or-later. Build system: CMake. Dependencies: none.

## Known compatibility
- Upstream root CMakeLists requires CMake 2.8; device CMake is 4.1.2.
- E187 applies. Conan CMakeToolchain sets `CMAKE_POLICY_VERSION_MINIMUM=3.5`; no source patch is planned.

## Test inventory (R51)
- Registered-CTest census: 0. Source `test*/` directories: 0. Root `CMakeLists.txt` has no `enable_testing()` and no `add_test()`; the only targets are one `ADD_LIBRARY(sisl ...)` plus the `FILE(GLOB sisl_APPS app/*.C)` loop that turns each `app/*prob.C` into its own `ADD_EXECUTABLE`.
- Asset census (the denominator used by the PR body, §12.72 demo/example口径): **26** = `app/*.C` 3 + `examples/` recursive `.cpp` 23 (top-level `example01`–`15` 15, `streaming/src/GoReadWrite.cpp` 1, `viewer/` 7). Counting commands are recorded in "Upstream test census evidence (R51)" below.
- **All 26 assets were built and, where they carry a `main()`, really executed on HarmonyOS PC on 2026-09-27 — see "Upstream test suite real execution" for the per-case table, the counts (18/18 runnable executables passed, 3/7 support translation units compiled, 5 blocked by the absent desktop OpenGL/GLUT stack, 0 failures) and the machine-readable summary.**
- Consumer test creates a 2D linear SISLCurve, evaluates it at `u=0.5` via `s1221`, and checks allocation, status, and both coordinates (4 assertions).

## Verification progress
- Device preflight passed twice; generated CMake recipe and metadata passed syntax/YAML validation.
- Local CMake configure/build/install passed; one library was staged.
- The generic build driver ran `make check`, which returned “No rule to make target 'check'”; that is consistent with the upstream having no registered tests.
- G2 attempt 1 failed because E017 rewrote GitHub to ghfast.top and that mirror timed out.
- G2 attempt 2 downloaded from official codeload, then rejected a mistyped SHA; the checksum is now corrected.
- G2 attempt 3 downloaded codeload successfully but Conan inferred ZIP from the extensionless URL; conandata now sets `filename: SISL-SISL-4.6.0.tar.gz`.
- G2 attempt 4 reported PASS but Step9 regenerated the consumer test to a printf stub; this result is invalid under R34 and was preserved for audit.
- A valid G2 rerun after restoring the API-backed consumer test passed; conan-create.log confirms test_sisl ran. Conan Verify reports G0/G1/G2/G3/G4 pass; L2/L4/L5 are pass-but-skipped because no package cache path was found. Finish then failed at W3 JC1/JC5 because tracked runtime markers in other package archives blocked the full-tree scan (first attempt only; superseded below). Manifest status is built from G2. Do not clean unrelated archives.

## Source URL and failure evidence
- Savannah .tar.gz returned HTTP 404: `~/tmp/uc2/sisl/attempt-001-savannah-404.txt`.
- G2 attempt 1 log: `~/tmp/uc2/sisl/conan-create-fail-001.log`.
- G2 attempt 2 log: `~/tmp/uc2/sisl/conan-create-fail-002.log`; command and first-error summary: `~/tmp/uc2/sisl/conan-create-fail-002.txt`.
- G2 attempt 3 log: `~/tmp/uc2/sisl/conan-create-fail-003.log`; attempt 4 stub-test PASS log/report: `~/tmp/uc2/sisl/conan-create-fake-test-pass.log`, `~/tmp/uc2/sisl/conan-verify-fake-test-pass.md`.
- Historical resource-gate failures delayed the corrected G2 attempt; evidence: `~/tmp/uc2/sisl/build-gate-fail-001.txt` through `build-gate-fail-013.txt`.

## Upstream test census evidence (R51)
- Inspected upstream tree: `/storage/Users/currentUser/tmp/uc2/sisl/builds/sisl-4.6.0.orig` (tarball SHA-256 b207fe6b4b20775e3064168633256fddd475ff98573408f6f5088a938c086f86, matches conandata.yml).
- `grep -rni "add_test|enable_testing|ctest|BUILD_TESTING" <tree>` -> 0 matches; `find <tree> -type d -iname 'test*'` -> 0 dirs. Sole CMakeLists.txt (root) has `CMAKE_MINIMUM_REQUIRED(VERSION 2.8)` and one `ADD_LIBRARY(sisl ...)`.
- How the static count 26 was obtained (reproducible on that same tree; this is the "取法" behind the PR body denominator):
  - `ls <tree>/app/*.C | wc -l` -> **3** (`s1013prob.C`, `s1320prob.C`, `s1606prob.C`)
  - `find <tree>/examples -name '*.cpp' | wc -l` -> **23** (15 top-level `example01`–`15` + `streaming/src/GoReadWrite.cpp` + `viewer/sisl_view_demo.cpp` + `viewer/src/{aux2,gl_aux,glutils,mouse,sisl_aux,transfutils}.cpp`)
  - 3 + 23 = **26**. `grep -cE '^[[:space:]]*(int|void)[[:space:]]+main[[:space:]]*\('` per file shows **19 with `main()`** (3 `app/*prob.C` + 15 `exampleNN.cpp` + `viewer/sisl_view_demo.cpp`) and **7 main-less support translation units** that are compile/link inputs of the others.
- The registered-CTest count is 0, but the 26 demo/example assets are the PR body's declared denominator, so they are what had to be executed. They have now been executed on device; see the next section. Nothing is filed under "unexecuted" any more, and nothing blocked is counted as passed.
- Consumer: 1 registered (`test_sisl`), 1 executed, 4 assertions, all pass. Re-counted `app/*prob.C`=3, `examples/*.cpp`=15, matching the figures above; these are demo/example executables, not a registered suite.

## W3 local CI re-run (supersedes the first finish attempt)
- W3 local CI PASSED: `.ci-result.json` -> exit_code 0, step W3_local_ci, timestamp 2026-09-23T18:59:39, log_sha256 8720dae46ee211c0f508f8c8f4ef68522683b32a6ad7707afc4437f3bdbe1538.
- `reports/w3-local-ci.log` tail: Total 1 / Success 1 / Failed 0; L0=pass L1=pass L2=skip(no bin/) L4=pass L5=pass. L1e destructive check moved lib/ and include/ away and the consumer test then failed to build => the test genuinely depends on sisl (R34).
- `reports/conan-create.log` lines 127-129: `Running test()` then `SISL linear curve evaluation passed`.
- Install went to the Conan package folder (`cmake --install ... --prefix <package_folder>`: lib/libsisl.a + 3 headers); nothing written to /storage/Users/currentUser/usr/local.
- No PR created and nothing pushed by this step.

## Upstream test suite real execution (2026-09-27, HarmonyOS PC build host A, runner `CIW-S4k3`)

This section replaces the earlier "0/26 not executed" declaration that PR review rule4 rejected. All 26 upstream
demo/example assets declared in the PR body were processed on device: every one was built, and every one that
carries a `main()` was actually run.

### Provenance and what was reused
- Upstream tree: `/storage/Users/currentUser/tmp/uc2/sisl/builds/sisl-4.6.0.orig`, extracted from
  `~/tmp/uc2/sisl/builds/sisl-4.6.0.tar.gz`, `sha256 = b207fe6b4b20775e3064168633256fddd475ff98573408f6f5088a938c086f86`
  (identical to `conandata.yml`).
- Library reused from the earlier window's build of the same tree, not rebuilt:
  `~/tmp/uc2/sisl/builds/sisl-4.6.0.work/build/libsisl.a`, `sha256 = 8c4e82fcd533fe967370953420f101c7a5df0280da913e8121eb2d4b578b6b70`,
  mtime `2026-09-23 13:41:30 +0800`, produced by upstream's own CMake (`CMakeCache.txt`:
  `CMAKE_C_COMPILER=/data/service/hnp/bin/clang`, `CMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++`, `CMAKE_BUILD_TYPE=Release`).
- Reuse was validated before use: `diff -rq <orig> <work>` over `src`, `app`, `include`, `examples` returned
  **0 differing files in each**, so the reused `libsisl.a` and the three `app/*prob.C` binaries correspond
  byte-for-byte to the official 4.6.0 source that this recipe downloads.
  Reused executables: `s1013prob` `sha256 edf5671d9b8f3f4a9e77947ca391374d49ddf8e2564d080e141f491470c34eb3`,
  `s1320prob` `sha256 cc24c79e38eea4c9386457f02e73d5cd1497ac0d2b60358623e3004289803584`,
  `s1606prob` `sha256 3ab53fd5dad5852bb0b7807151d732fe6adf50e55a842650d1f3f427b3541794` (mtimes 2026-09-23 13:41:32/32/33).
- Newly built and run by this runner: everything under `examples/` (16 executables + 7 translation units),
  2026-09-27 15:33–15:35 +0800. Runner script sha256 `80a8a095f9c6c2ec318795a8838da2d1703faa0369341c0076d0e9b2a1caf130`.
- Compiler: `clang version 15.0.4 (/srv/workspace/llvm-release/2026_0313_llvm15_release/toolchain/llvm-project/clang 0e01a01d567b9acfce8edfdadb66a7b69f088fb0)`, host `HarmonyOS HongMeng Kernel 1.12.0 aarch64`.

### Why the examples are compiled by hand (upstream's own example build entry is broken in the release tarball)
`examples/Makefile` is the single line `include ../makefile_template`, and the released tarball does not ship
`makefile_template`. Verbatim first error from `make -f Makefile` in `examples/`:

```
Makefile:1: ../makefile_template: No such file or directory
make: *** No rule to make target '../makefile_template'.  Stop.
```

The same applies to `examples/viewer/Makefile` and `examples/streaming/Makefile` (both are only that include).
So the examples were compiled with the same toolchain the recipe uses, against the upstream-registered `sisl` library:

```
clang++ -std=c++11 -O2 -I<tree>/include -I<tree>/examples/streaming/include \
  -o <bin>/exampleNN <tree>/examples/exampleNN.cpp \
  <tree>/examples/streaming/src/GoReadWrite.cpp <build>/libsisl.a -lm
```

### Success predicate (read off upstream's own sources, not invented here)
Every `examples/exampleNN.cpp` ends with:

```
    } catch (exception& e) {
        cerr << "Exception thrown: " << e.what() << endl;
        return 0;
    }

    return 1;
```

**so `1` is upstream's success code and `0` means SISL threw.** An example is therefore PASS iff `rc == 1`,
its output contains no `Exception thrown` line, every `IN_FILE_*` it reads was present and non-empty, and every
`OUT_FILE_*` it declares was produced and non-empty. `app/*prob.C` are plain programs: PASS iff `rc == 0` with
non-empty output. The 7 translation units without `main()` cannot be "run" as cases; they are gated by their
compiler rc and are exercised as link inputs of the 15 executed examples.

### 测试统计表（分母口径 = PR 正文 §12.72 申报的 26 个上游演示/示例资产；静态计数取法见上一节）

| 测试类型 | 上游用例数 | 本轮处理 | 通过 | 失败 | 受阻未执行 | 判定依据 |
|---|---|---|---|---|---|---|
| 单元测试（CTest 注册口径） | 0 | 0 | 0 | 0 | 0 | 上游根 `CMakeLists.txt` 无 `enable_testing()`/`add_test()`，注册数确为 0 |
| 集成测试（CTest 注册口径） | 0 | 0 | 0 | 0 | 0 | 同上 |
| 其他测试 — `app/*prob.C`（上游 `FILE(GLOB sisl_APPS app/*.C)` + `ADD_EXECUTABLE` 注册目标） | 3 | 3 | 3 | 0 | 0 | `rc==0` 且输出非空（几何数值结果） |
| 其他测试 — `examples/example01–15.cpp`（链式工作流，共用一个 CWD） | 15 | 15 | 15 | 0 | 0 | `rc==1`（上游成功码）+ 无 `Exception thrown` + 声明的 IN/OUT 文件全部非空产出 |
| 其他测试 — `examples/viewer/sisl_view_demo.cpp` | 1 | 1 | 0 | 0 | 1 | 构建期缺 `GL/glut.h`，第一条真实错误见下 |
| 其他测试 — `examples/` 下 7 个无 `main()` 支撑翻译单元 | 7 | 7 | 3 | 0 | 4 | 编译器 rc；4 个缺 GL 头文件 |
| **上游合计（资产口径）** | **26** | **26** | **21** | **0** | **5** | 其中 **19 个带 `main()` 的可执行用例真跑**（18 通过 + 1 构建受阻），7 个支撑 TU 作编译/链接输入 |
| **鸿蒙特有测试** — `test_package/test.c`（消费者 `test_sisl`，`newCurve`+`s1221`+`freeCurve`） | 1 | 1 | 1 | 0 | 0 | 4 项断言，`conan create` 内实际执行（见 `reports/conan-create.log`） |
| **总计** | **27** | **27** | **22** | **0** | **5** | 上游 26 + 鸿蒙特有 1 |

**Verdict** PASS — 上游 26 项全部处理：21 通过 / 0 失败 / 5 受阻于平台缺桌面 OpenGL·GLUT；可执行用例真跑 18/19 通过。
Runner exit code: `runner_exit_code: 0`（0 = 本轮没有任何 FAIL/BUILD_FAIL 行；见下方机器可读汇总）。

### 逐用例明细（26 行，与设备侧 `~/tmp/uc2/ciw-s4-sisl-b3/logs/cases2.tsv` 同源）

| 上游资产 | 形态 | 执行/构建 | 观测 | 判定 | 第一条真实错误 |
|---|---|---|---|---|---|
| app/s1013prob.C | executable | rc=0 | outbytes=24 | PASS | — |
| app/s1320prob.C | executable | rc=0 | outbytes=8 | PASS | — |
| app/s1606prob.C | executable | rc=0 | outbytes=404 | PASS | — |
| examples/example01.cpp | executable | rc=1 | out=2/376 B in=0 exc=0 selfchk=2 | PASS | — |
| examples/example02.cpp | executable | rc=1 | out=2/626 B in=0 exc=0 selfchk=2 | PASS | — |
| examples/example03.cpp | executable | rc=1 | out=1/346 B in=2 exc=0 selfchk=4 | PASS | — |
| examples/example04.cpp | executable | rc=1 | out=1/398 B in=1 exc=0 selfchk=3 | PASS | — |
| examples/example05.cpp | executable | rc=1 | out=1/373 B in=0 exc=0 selfchk=2 | PASS | — |
| examples/example06.cpp | executable | rc=1 | out=3/594 B in=0 exc=0 selfchk=4 | PASS | — |
| examples/example07.cpp | executable | rc=1 | out=0/254 B in=1 exc=0 selfchk=2 | PASS | — |
| examples/example08.cpp | executable | rc=1 | out=3/506 B in=0 exc=0 selfchk=4 | PASS | — |
| examples/example09.cpp | executable | rc=1 | out=2/637 B in=0 exc=0 selfchk=2 | PASS | — |
| examples/example10.cpp | executable | rc=1 | out=2/354 B in=0 exc=0 selfchk=3 | PASS | — |
| examples/example11.cpp | executable | rc=1 | out=1/202 B in=0 exc=0 selfchk=2 | PASS | — |
| examples/example12.cpp | executable | rc=1 | out=1/492 B in=2 exc=0 selfchk=4 | PASS | — |
| examples/example13.cpp | executable | rc=1 | out=1/557 B in=2 exc=0 selfchk=5 | PASS | — |
| examples/example14.cpp | executable | rc=1 | out=2/785 B in=0 exc=0 selfchk=4 | PASS | — |
| examples/example15.cpp | executable | rc=1 | out=1/1320 B in=1 exc=0 selfchk=8 | PASS | — |
| examples/viewer/sisl_view_demo.cpp | executable | build_rc=1 | - | BLOCKED | examples/viewer/sisl_view_demo.cpp:52:10: fatal error: 'GL/glut.h' file not found |
| examples/streaming/src/GoReadWrite.cpp | support-tu | compile_rc=0 | - | COMPILED | — |
| examples/viewer/src/aux2.cpp | support-tu | compile_rc=0 | - | COMPILED | — |
| examples/viewer/src/gl_aux.cpp | support-tu | compile_rc=1 | - | TU_BLOCKED | examples/viewer/include/gl_aux.h:44:10: fatal error: 'GL/glut.h' file not found |
| examples/viewer/src/glutils.cpp | support-tu | compile_rc=1 | - | TU_BLOCKED | examples/viewer/include/glutils.h:44:12: fatal error: 'GL/glx.h' file not found |
| examples/viewer/src/mouse.cpp | support-tu | compile_rc=1 | - | TU_BLOCKED | examples/viewer/src/mouse.cpp:42:10: fatal error: 'GL/glut.h' file not found |
| examples/viewer/src/sisl_aux.cpp | support-tu | compile_rc=0 | - | COMPILED | — |
| examples/viewer/src/transfutils.cpp | support-tu | compile_rc=1 | - | TU_BLOCKED | examples/viewer/src/transfutils.cpp:40:10: fatal error: 'GL/glut.h' file not found |

Column key: `out=<n>/<bytes> B` = declared `OUT_FILE_*` produced / program stdout size; `in` = declared `IN_FILE_*`
prerequisites satisfied; `exc` = `Exception thrown` lines in output; `selfchk` = upstream's own `jstat != ...` and
`throw runtime_error` guard count in that file (so "no exception" means SISL returned success status, not silence).

Functional side-evidence: the 15 examples form one chained workflow and produced all **23** declared Go-format
data artifacts non-empty in the run directory — `example1_curve.g2`, `example1_points.g2`, `example2_curve.g2`,
`example2_points.g2`, `example3_curve.g2`, `example4_curve.g2`, `example5_curve.g2`, `example6_curve_1.g2`,
`example6_curve_2.g2`, `example6_isectpoints.g2`, `example8_curve_1.g2`, `example8_curve_2.g2`,
`example8_closestpoints.g2`, `example9_points.g2`, `example9_surf.g2`, `example10_curves.g2`,
`example10_surf.g2`, `example11_surf.g2`, `example12_isectpoints.g2`, `example13_isectcurves.g2`,
`example14_curve.g2`, `example14_points.g2`, `example15_points.g2` — which is what downstream examples
(`example03`/`04`/`07`/`12`/`13`/`15`) read back in, so the geometry pipeline ran end to end rather than
returning early.

### The 5 blocked assets, with the missing dependency measured rather than asserted
- `GL/glut.h` and `GL/glx.h` are not in the platform SDK:
  `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/GL/` contains only
  `gl.h`, `glcorearb.h`, `glext.h`.
- No GLUT/desktop-GL runtime anywhere on the machine: `find /data/service/hnp /usr <home>/usr <home>/.harmonybrew
  -name 'glut*'` -> 0 hits; no `libGL.so`, `libGLU`, `libglut`. The sysroot carries only the GLES family
  (`libEGL.so`, `libGLESv2.so`, `libGLESv3.so`, `libGLv4.so`). `pkg-config --exists gl` -> false.
- Nothing to pull from the artifact repository either: `conan list "glut/*" -r=ohpcd` ->
  `Found 0 pkg/version recipes matching glut/* in ohpcd`; same for `opengl/*`.
- The SISL viewer is written against desktop OpenGL + GLUT + GLX (`#include <GL/glut.h>`, `"GL/glx.h"`),
  so these 5 assets need a new upstream-independent port, not a build flag. They are reported as blocked with
  their first real error above and are **not** counted as passed.

### Machine-readable summary (same source as the two tables above)

```json
{
  "package": "sisl/4.6.0",
  "runner": "CIW-S4k3",
  "date": "2026-09-27T15:35:29+0800",
  "host": "HarmonyOS HongMeng Kernel 1.12.0 aarch64",
  "compiler": "clang version 15.0.4 (/srv/workspace/llvm-release/2026_0313_llvm15_release/toolchain/llvm-project/clang 0e01a01d567b9acfce8edfdadb66a7b69f088fb0)",
  "source_tarball_sha256": "b207fe6b4b20775e3064168633256fddd475ff98573408f6f5088a938c086f86",
  "upstream_assets_declared": 26,
  "rows_in_this_runner": 26,
  "executable_cases": 19,
  "executable_cases_passed": 18,
  "executable_cases_failed": 0,
  "executable_cases_build_failed": 0,
  "executable_cases_blocked": 1,
  "support_translation_units": 7,
  "support_tus_compiled": 3,
  "support_tus_blocked": 4,
  "upstream_pass_total": 18,
  "upstream_fail_total": 0,
  "go_format_output_files": 23,
  "first_error_glut_not_found_rows": 4,
  "first_error_glx_not_found_rows": 1,
  "runner_exit_code": 0,
  "pass_rule": "app: rc==0 with non-empty output; example: rc==1 (upstream success code) and no 'Exception thrown' line and all declared IN_FILE_* inputs present and all declared OUT_FILE_* produced non-empty; support TU: compiler rc==0"
}
```

### Reproduce
```bash
sh ~/tmp/uc2/gate.sh 8000
sh ~/tmp/uc2/build-slot.sh --kind long --wait 3600 --mem 6000 -- \
  sh ~/tmp/uc2/ciw-s4-sisl-b3/run_def.sh
```
Resource discipline actually observed for this run: `gate.sh` -> `GATE_PASS:probe=clang MemAvailable=19674MB`;
`build-slot.sh` -> `SLOT_OK 15:30:56 cmd=sh .../run_def.sh` … `SLOT_DONE:ok`; sampler
`PEAK_COMPILER_RSS_KB=155956` (~152 MB), `MIN_MemAvailable_KB=19404800` (~18.5 GB), concurrency 1.
Device-side artifacts of this run (not part of the PR): `~/tmp/uc2/ciw-s4-sisl-b3/logs/{cases2.tsv,summary.json,
upstream-suite.txt,run/*,build/*}`, `~/tmp/uc2/ciw-s4-sisl-b3/run_def.sh`, run directory
`~/tmp/uc2/ciw-s4-sisl-b3/run-ex/` (the 23 `.g2` files, mtimes 2026-09-27 15:34–15:35).

### What this run did not touch
No build input was modified: `conanfile.py`, `conandata.yml`, `patches/`, `test_package/conanfile.py`,
`test_package/CMakeLists.txt` and `test_package/test.c` are byte-identical to the state that produced the current
W3/`conan create` evidence, so the recipe revision and the published package are unchanged. The upstream examples
were deliberately **not** wired into `build()`: doing so would change the recipe revision and invalidate the
already-collected W3/G2 evidence, and it would make `conan create` depend on a desktop-GL port that this platform
does not have. The 5 GL-blocked assets stay declared as blocked.

---

**编译结束**: 2026-09-23 18:57
**最终状态**: built
