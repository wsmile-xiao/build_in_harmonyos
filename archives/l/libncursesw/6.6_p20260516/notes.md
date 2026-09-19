# libncursesw 6.6_p20260516 adaptation notes

## Baseline

- Official stable release: 6.6, 2025-12-30
- Source SHA-256: `355b4cbbed880b0381a04c46617b7656e362585d52e9cf84a67e2009b749ff11`
- Build system: Autotools
- Conan reference: `libncursesw/6.6_p20260516`
- Third-party Conan prerequisites: none
- Independent OHOS device shadow CI passed for `ecce6bcdd8093895839faffe9a13051d8576d1e3`.
  Official PR CI and AI review are pending; see `reports/knowledge-evidence.md`.

## Package contract

- Build static wide-character libraries only. Shared ncurses libraries can shadow the
  platform `libncursesw.so.6` and are rejected by the recipe.
- Preserve all 86 entries declared by upstream `test/programs` and run the complete
  upstream `make -j1 check` target.
- Install public headers at the top-level include directory, all five static library
  components, the command-line tools, and the complete terminfo database.
- Export the CMake `FindCurses` contract, the Conan `libncursesw::libncursesw` target, and
  relocatable upstream `ncursesw6-config` and pkg-config metadata. The consumer tests
  cover wide-character curses, `tputs`, terminfo, window, panel, menu, form, and both
  metadata-driven static-link interfaces.

## Adaptation

1. `0001-detect-compound-expr.patch` rejects the platform `expr` implementation when it
   cannot evaluate Autoconf compound expressions, allowing the GNU implementation
   already present in the build environment to be selected.
2. `0002-lib-mvcur-static-link.patch` permits the upstream `lib_mvcur` test to override its
   intentional stub symbols during a static link.
3. `0003-install-headers-shell.patch` invokes the generated header installer through the
   configured shell on HMDFS.
4. `0004-config-guess.patch` makes the upstream platform detector return
   `aarch64-unknown-linux-ohos` without supplying `--build`, `--host`, or `--target`.
5. `ac_cv_func_setfsuid=no` prevents the configure probe from executing unsupported
   syscall 151 in the target sandbox. No source or patch uses an OHOS preprocessor
   conditional.

These patches are copied from the existing `ncurses/6.6` recipe; their SHA-256
values are recorded in `conandata.yml`. Application to this independent reference
must be verified in its own build.

## Validation

Validation used the authorized HarmonyOS arm64 device, an isolated source
snapshot, and a fresh Conan home. Upstream compilation and tests used `make -j1`.
The test-package CMake helper appended `-j1` after Conan's default job argument;
GNU Make applies the final job argument.

The retained device run `ecce6bcdd809-20260916T144447Z-21138` reported:

- Upstream `test/programs`: 86/86 **program build entries**, not 86 passing test cases
- Complete upstream `make -j1 check`: completed; no upstream assertion count reported
- Installed terminfo database: 2,874 files
- Added consumer workflows: 8/8 ran (two direct and six metadata-driven)
- Internal consumer assertions: 27/27
- Negative configurations: `shared=True` rejected (exit 6), missing terminfo
  rejected by the consumer (exit 1)
- Build-system detection: `aarch64-unknown-linux-ohos`
- Six metadata linker traces selected only packaged static archives
- Packaged shared libraries: 0; five static libraries installed

L0/L1/L2/L4/L5 passed in the isolated device run. L2 also warned that ten
upstream commands do not support generic `--version`/`--help` probing; this was
nonblocking, not ten passing CLI help tests. The source pre-download failed and
Conan downloaded the hash-checked source. These device results do not establish
that the official PR pipeline has passed.

The eight executed workflows are the two direct consumers plus `ncursesw6-config` and the
`formw`, `menuw`, `ncurses++w`, `ncursesw`, and `panelw` pkg-config consumers.
The old `ncurses/6.6` recipe revision and package ID do not identify this package.

The evidence report binds the exact candidate HEAD, device, package reference,
run log, and generated metadata. No result from `ncurses/6.6` or another
HarmonyOS device is presented as a run of this reference.

## Platform CI and finish boundary

The isolated device run exited 0 and its log hashes are recorded in the evidence
report. It was not the platform's `finish`/W3 closure and has no claimed W3
`.ci-result.json`. The PR must independently inspect its current-HEAD CI result,
including W3 evidence if that pipeline requires it, and report any broader
`finish` failure separately. A local L0-L5 pass does not imply PR acceptance.
