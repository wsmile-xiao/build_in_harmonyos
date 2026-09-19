# libncurses 6.6_p20260516 test report

## Scope

- Package: `libncurses/6.6_p20260516` (static narrow-character ncurses, Autotools)
- Target: HarmonyOS PC, `aarch64-unknown-linux-ohos`
- Recipe: `conan create` with `ci/conan/profiles/ohos-aarch64` (os=OHOS, arch=armv8,
  compiler=clang 15, Release)
- Upstream suite: the complete `make -j1 check` target, executed inside `conan build()`

## Upstream test inventory and result

Upstream ncurses 6.6 ships no unit-test framework. Its verification surface is the
`make check` target, which contains three groups:

| Group | Entries | Result | Evidence |
|---|---|---|---|
| `test/programs` program entrypoints | 86 | 86/86 built | recipe verifies all 86 targets exist after `make` |
| Header self-containment compilations | 57 | 57/57 | `** testing <header>` lines for `include/`, `ncurses/`, `panel/`, `menu/`, `form/`, `test/`, `c++/` |
| `link_test` API link-completeness | 1 | 1/1 | links every implemented public entry point against `libncurses.a` |
| **Total** | **144** | **144/144 (100%)** | `make -j1 check` exit code 0 |

Upstream `make check` builds the interactive `test/` programs but does not run them
(upstream prints "The test-programs are interactive"); this adaptation does not change
that behaviour and does not claim them as executed test cases.

No upstream test case was modified, deleted or weakened by this adaptation. The
`0005-link-test-ext-colors.patch` patch changes which entry points the generated
`link_test.c` may reference — and only in the non-wide configuration, where the
extended-color API is not implemented by upstream either; it does not alter any test
assertion.

## Added consumer tests (test_package)

Every consumer is compiled with the target clang, linked against the packaged static
archives (verified with `-Wl,-t` link traces that only packaged archives are selected)
and executed on the HarmonyOS target.

Each metadata consumer contributes three assertions: the metadata path flags must point
into the Conan package (`-I` for `--cflags`), the same for `-L` in the link flags, and the
compile/link trace plus the run of the produced binary must select only packaged static
archives. The `test_*` programs report their own assertion totals (7, 3, 4 and 7).

| # | Workflow | Interface under test | Assertions | Result |
|---|---|---|---|---|
| 1 | `test_curses_module` | Conan CMake config `libncurses::libncurses` | 7 | 7/7 |
| 2 | `test_ncurses_components` | panel / menu / form lifecycles | 3 | 3/3 |
| 3 | `test_ohos_platform` | HarmonyOS platform contract | 4 | 4/4 |
| 4 | `test_find_curses_module` | upstream CMake `FindCurses` module | 7 | 7/7 |
| 5 | config-script consumer | relocatable `ncurses6-config` | 3 | 3/3 |
| 6 | `form` consumer | pkg-config module `form` | 3 | 3/3 |
| 7 | `menu` consumer | pkg-config module `menu` | 3 | 3/3 |
| 8 | `ncurses++` consumer | pkg-config module `ncurses++` (C++) | 3 | 3/3 |
| 9 | `ncurses` consumer | pkg-config module `ncurses` | 3 | 3/3 |
| 10 | `panel` consumer | pkg-config module `panel` | 3 | 3/3 |
| | **Consumer totals** | | **39** | **39/39** |

### HarmonyOS-specific contract

Three of the consumer workflows verify properties that only exist on the HarmonyOS PC
target and that are the reason this package is built statically:

- `test_ohos_platform` confirms at runtime that `uname()` reports HarmonyOS, that
  `/proc/self/maps` contains no shared `libncurses*`/`libtinfo*`/`libform*`/`libmenu*`/
  `libpanel*` object, and that the packaged terminfo database drives a real window
  update (4 assertions).
- The package-level contract in `test_package/conanfile.py` verifies that the package
  ships no shared object, that all five static archives are present, that a consumer
  built from the packaged `ncurses6-config` metadata is an AArch64 target binary and that
  this binary has no `DT_NEEDED` entry for any curses or tinfo library (4 assertions).

This matters because a shared ncurses/tinfo library shipped by a package can shadow the
platform terminal library that the system shell links; the static narrow package removes
that risk while keeping the 8-bit ABI available.

### Negative tests

| Check | Expected | Result |
|---|---|---|
| `shared=True` configuration | rejected by `configure()` | rejected (pass) |
| Destructive re-run of `test_package` with `bin/`, `lib/` and `include/` removed | must fail | fails (pass) — the consumer tests genuinely depend on the packaged artifacts |

## Totals

| Metric | Value |
|---|---|
| Upstream `make check` entries passed | 144/144 (100%) |
| Added HarmonyOS consumer workflows | 10 |
| Consumer assertions passed | 39/39 |
| Package-level HarmonyOS assertions passed | 4/4 |
| Total added assertions | 43/43 (100%) |
| Upstream test cases modified | 0 |

## Package contents verified

| Artifact | Value |
|---|---|
| Headers | 18 files under `include/` (`curses.h`, `ncurses.h`, `form.h`, `menu.h`, `panel.h`, `term.h`, …) |
| Static archives | `libncurses.a`, `libform.a`, `libmenu.a`, `libpanel.a`, `libncurses++.a` |
| Shared libraries | 0 |
| Utilities | `tic`, `infocmp`, `infotocap`, `captoinfo`, `toe`, `tput`, `tset`, `clear`, `reset`, `tabs`, `ncurses6-config` |
| pkg-config modules | `ncurses.pc`, `form.pc`, `menu.pc`, `panel.pc`, `ncurses++.pc` (all relocatable) |
| terminfo database | `tic` reports 2897 entries; 2872 files under `share/terminfo` in the built package |
| Build-system detection | `aarch64-unknown-linux-ohos` |

## Reproduce

```bash
# W3 local CI simulation (same scripts as the platform pipeline)
zsh ci/conan/setup.sh
CI_PACKAGES=archives/l/libncurses/6.6_p20260516 \
  zsh ci/conan/build_and_test.sh archives/l/libncurses/6.6_p20260516

# Direct recipe validation
conan create archives/l/libncurses/6.6_p20260516 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```
