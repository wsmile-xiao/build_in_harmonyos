# isoimagewriter 26.04.0 verification report

## Environment

- OpenHarmony / HarmonyOS PC aarch64
- clang 15.0.4 (`aarch64-linux-ohos`), Conan 2.29.1, CMake 4.1.2, ECM 6.26.0
- Qt 6.11.1 (`qtbase-sql-dbus`), KF6 6.26.0 (karchive / kcoreaddons / kcrash /
  ki18n / kiconthemes / kwidgetsaddons / solid)

## Upstream test inventory (R51 step 1)

| Check | Command | Result |
|-------|---------|--------|
| test files | `find . -iname "*test*"` | 0 |
| CTest registration | `grep -rn "enable_testing\|add_test" CMakeLists.txt isoimagewriter/CMakeLists.txt` | 0 (only `find_package(Qt6 ... Test)`) |
| autotests dir | `ls autotests/` | does not exist |

Upstream test count **N = 0** → step 2 (run upstream tests) is 0/0, not
applicable. Per R51 step 3 a consumer test was added.

## Validation performed

- `conan create archives/i/isoimagewriter/26.04.0 -pr:h=ci/conan/profiles/ohos-aarch64
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`: exit 0
- `conan-verify isoimagewriter 26.04.0`: G1 pass / G2 pass (clean `conan create`) /
  G3 pass / G4 pass; its L2 / L4 / L5 lines report PASS but are marked
  `⏭️ 跳过（无 cache 路径）` in `reports/conan-verify-report.md` — i.e. they did
  **not** actually execute (`conan-verify` found no cache path for the package
  id). The W3 simulation below is the authoritative evidence for L2 / L4 / L5.
- W3 local CI simulation (`finish` step [5/10]): `JC pass / KC pass / G0 pass /
  L0 pass / L1 pass / L1e pass / L5 pass`, `.ci-result.json` exit_code=0.
  Two harness lines are reported as non-pass and are documented in full here:

  | Harness line | Actual value | Reason |
  |--------------|--------------|--------|
  | `L2_RESULT` | `skip` | `ci/conan/build_and_test.sh` runs `bin/isoimagewriter --version` with the inherited environment only, without assembling the dependency `lib/` paths. The loader therefore cannot resolve the Qt6/KF6 shared libraries and the process exits 127 (measured: running the packaged binary with no environment gives exit 127; the same holds with only the package's own `lib/`+`bin/` on `LD_LIBRARY_PATH`, since the KF6 dependency packages additionally carry E537-shaped `DT_NEEDED` entries). Qt GUI binaries also need `QT_QPA_PLATFORM=offscreen`. The harness marks L2 as non-blocking by design, and the identical binary runs clean in `test_package`, which assembles the runtime environment — see the test_package section below. |
  | `L4_RESULT` | `warn` | The harness scans `patches/` for `(strcpy\|sprintf\|gets\|strcat)\b`; the pattern matches the substring `gets` inside `KF6::IconWidgets` on patch line 35. It is a false positive of the scanner, not an introduced dangerous function — the patch only adds `OR CMAKE_SYSTEM_NAME STREQUAL HarmonyOS` to three platform branches. Non-blocking. |

  `finish` step [3/10] (`clean_verify.py`) is skipped for this package: that tool is
  autotools-only (it hard-codes `./configure`) while isoimagewriter is a CMake
  project. The step is non-blocking by the SKILL contract; the authoritative build
  evidence is G2 `conan create` and the W3 simulation above.

## test_package (HarmonyOS-specific test)

The test executes the packaged binary, which is the only automated coverage the
project has:

| # | Assertion | Result |
|---|-----------|--------|
| 1 | `isoimagewriter` present in the dependency graph with a package folder | PASS |
| 2 | packaged `bin/isoimagewriter` exists | PASS |
| 3 | `share/applications/org.kde.isoimagewriter.desktop` installed | PASS |
| 4 | `share/icons/hicolor/scalable/apps/org.kde.isoimagewriter.svg` installed | PASS |
| 5 | `--version` exits 0 and identifies the application | PASS |
| 6 | packaged binary embeds the version string `26.04.0` | PASS |
| 7 | `--help` advertises `--version` | PASS |
| 8 | `--help` advertises `--lang` | PASS |
| 9 | `--help` advertises `--dir` | PASS |

- Test cases: 1 (9 assertions)
- Passed: 1
- Failed: 0
- Skipped: 0
- Runtime-linking repair applied inside the test (E537): 2 relative and 5 stale
  absolute DT_NEEDED entries materialized from the dependency packages.

Observed output:

```
$ bin/isoimagewriter --version
isoimagewriter

$ bin/isoimagewriter --help
Usage: .../bin/isoimagewriter [options] [File]
Write an ISO Image to a USB Disk

Options:
  -v, --version              Displays version information.
  --lang <language>
  --dir <path>
  ...
Arguments:
  [File]                     ISO file to open
```

`--version` reports an empty applicationVersion because upstream handles the
option before `KAboutData::setApplicationData()`; the packaged release is
verified through the embedded version string instead.

## Result

- Upstream test pass rate: 0/0 (not applicable; N=0 with inventory evidence)
- Added test pass rate: 1/1 (100%)
- Build status: passed
- Known limitation: ISO signature verification is compiled out (upstream's
  optional QGpgmeQt6 binding is not published); the write and read-back
  verification path is unaffected.
