# tabbed 0.9 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device (A machine)
- Clang 15.0.4 (`/data/service/hnp/bin/clang`, Target: aarch64-unknown-linux-ohos)
- Conan 2.29.1 (OHOS-adapted), profile `ci/conan/profiles/ohos-aarch64`
- CONAN_HOME: task-private home (conancenter disabled, ohpcd enabled)

## Verification

- `preflight_check.sh tabbed/0.9`: exit 0 (fontconfig/2.18.3, libx11/1.8.13,
  libxft/2.3.9, xorgproto/2025.1 all published; version not taken)
- `conan-verify tabbed 0.9`: exit 0, verdict PASS
  - G0 pre-scan: PASS (non-blocking)
  - G1 recipe completeness: PASS
  - G2 `conan create`: PASS (test_package executed, 4/4). Note on provenance: the
  archived `conan-create.log` is a **re-run with the dependency closure already in the
  local cache**: its 20 `Already installed!` lines are the same 10 package-ids in two
  passes (`(1 of 10)` .. `(10 of 10)`), and it contains no `Calling build()` or
  `Calling package()` line at all. The real from-source evidence is
  `tabbed/0.9: Forced build from source` (W3 log line 173).
  - G3 system-lib isolation (R26): PASS (application package, no lib/)
  - G4 artifact completeness: PASS with warning — package-id regex in
    `scripts/ohc/conan_verify.py:601` does not match dotted versions
    (`\w` vs `0.9`), so L2/L4/L5 take the "no cache path" skip branch.
    Framework-side defect, recorded in the registry. The W3 run below
    executes L0-L5 itself: **L0/L1/L1e/L4/L5 pass, L2 skip** (see the itemised
    line under the `finish` bullet, and `L2_RESULT=skip` in the W3 log).
- `finish tabbed 0.9 built` → W3 local CI: exit 0
  - `.ci-result.json`: exit_code=0, step=W3_local_ci,
    timestamp=2026-09-24T23:31:19.669565, integrity=8f88dfeee375fb75,
    log_sha256=b0ad496fcaf0c4dca2e2f8e78a3ca805b7e1e6e55448cddc68b5ac02aecc1ba6
    (re-verified with `sha256sum reports/w3-local-ci.log`: byte-identical to the value
    above).  This run certifies the build() with the `unset LD_LIBRARY_PATH` link-stage
    fix.  Two earlier runs are superseded history and must not be quoted as current
    evidence: integrity 563a3de4d09831ff (14:01:37) and 94630e5e587ee691 (22:12:58).
  - L0: passed · L1: passed · L1e R34 negative test: passed
    (`test genuinely depends on tabbed`) · L2: skipped (documented:
    tabbed has no `--version`/`--help`, all early exits go through
    `die()`; smoke rule is non-blocking) · L4: passed · L5: passed
  - Build summary: Total 1 / Success 1 / Failed 0, pass rate 100.0%
  - Junk check ran in incremental mode over this package's files: `Junk Files: 0`

## Upstream tests (R51 three-step)

- Static inventory: **0** (tarball unpacks to 9 files, no test assets;
  Makefile `.PHONY` measured as `all clean dist install uninstall` only —
  no check/test target; `assert(` counter 0, `<assert.h>` never included)
- Actually executed: **0** (nothing to run — upstream ships no tests)
- Skipped: **0**

## test_package (consumer)

`test_tabbed.sh` really executes the two packaged programs and asserts on
stderr text (exit codes carry no information upstream: `-v` also exits 1
via `die()`):

1. `tabbed -v` → first line `tabbed-0.9, …` (proves -DVERSION not
   normalized)
2. `tabbed -Z` (unknown option) → usage banner `tabbed [-dfksv]`
3. `tabbed` with no DISPLAY → reaches `XOpenDisplay`, prints
   `cannot open display` (proves the libX11/libXft/libfontconfig runtime
   closure loads)
4. `xembed only-one-arg` → its own usage line

Runtime note (E452): the registry copy of fontconfig/2.18.3 carries a
`.codesign` the current loader rejects (load-time failure → rc=127), so
`test()` materializes the dependency closure into a task-private `~/tmp`
directory, re-signs the copies there (`llvm-objcopy --remove-section
.codesign` + `binary-sign-tool … -selfSign 1`), prepends that directory to
`LD_LIBRARY_PATH`, and removes it in `finally`. The Conan cache is only
ever read from (E452 forbid). Log line: `E452: re-signed 36 private
runtime copies`.

Raw lines from this run's W3 log (quoted so the numbers are checkable without the
log itself, which is not part of the PR):

```
296:PASS: tabbed -v reports version 0.9 on stderr (rc=1)
297:PASS: tabbed prints usage on an unknown option (rc=1)
298:PASS: tabbed reaches XOpenDisplay and reports cannot open display (rc=1)
299:PASS: xembed prints its usage line with too few arguments (rc=2)
300:TABBED_CHECK_SUMMARY checks=4 fails=0
320:L2_RESULT=skip: tabbed version/help failed, xembed failed
173:tabbed/0.9: Forced build from source
294:tabbed/0.9 (test package): E452: re-signed 36 private runtime copies
```

- Test cases: 4 · Passed: **4** · Failed: 0 · Skipped: 0
  (`TABBED_CHECK_SUMMARY checks=4 fails=0`)
- Peak RSS: declared **5 MB** (`test_package/MANIFEST.yml` max_rss_mb: 5), measured
  with `memcap-run.py --probe` inside the remediated runtime (re-signed closure).
  Honest boundary: the probe's raw stdout is **not archived**, so this is a declared
  value, not gate evidence -- no gate (G0-G4 / L0-L5 / W3) reads it.  Reproduce with
  `memcap-run.py --probe -- sh test_tabbed.sh` during a `conan create`.

## Result

The recipe was verified on an OpenHarmony aarch64 device (W3 exit 0,
consumer 4/4). `manifest.yaml` keeps `status: built`: **published** additionally
requires CI upload evidence on the merged HEAD, which is reported after CI is
green, not by this local run.
