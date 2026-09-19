# libpanelw 6.6_p20260516 test report

## Environment

- Target: HarmonyOS 6.0, arm64
- Device: one currently authorized device, recorded in the retained W3 closure
- Compiler: Clang 15 with libc++
- Conan: 2.29.1
- Candidate: exact final HEAD and tree recorded in the retained W3 closure and PR body

## Results

| Category | Passed | Total | Result |
|---|---:|---:|---|
| Upstream test/program entrypoints | 86 | 86 | PASS |
| Added consumer programs | 2 | 2 | PASS |
| Internal consumer and harness assertions | 21 | 21 | PASS |
| Negative configurations | 1 | 1 | PASS |

The complete upstream `make -j1 check` target passed, and every `test/programs`
entrypoint of the 20260516 snapshot built, including the panel consumer
`demo_panels`, which was additionally executed headless (piped `q` input,
`TERM=xterm` with the packaged terminfo) and exited 0 with rendered panel
output. The two added consumer programs are `test_panel_consumer` (13 panel
deck lifecycle assertions through the `libpanelw::libpanelw` CMake target) and
`test_panel_pkgconfig` (the `panelw.pc` pkg-config consumer whose `-Wl,-t`
link trace selected the packaged `libpanelw.a` together with the ncurses
package `libncursesw.a`, linked no shared curses library, and exited 0 at
runtime). The negative configuration `libpanelw/*:shared=True` is rejected at
`configure()` with the static-only invalid-configuration message.

## Evidence

- Recipe revision: `17713e66de2fa5038dd38327f540c836`
- Package ID: `044971e9092dd6608b4c967bac722a276b7cc911`
- The exact package revision, candidate HEAD/tree, authorized device, result archive,
  W3 log, `.ci-result.json` integrity value, and evidence-manifest hash are run-level
  values. They are recorded together in the retained exact-current W3 closure and PR
  body after the final candidate is immutable.
- Acceptance requires every retained evidence hash to match and the automatically
  generated `.ci-result.json` to report `exit_code=0`.
