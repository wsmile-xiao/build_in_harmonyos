# ncurses 6.6 adaptation notes

## Baseline

- Official stable release: 6.6, 2025-12-30
- Source SHA-256: `355b4cbbed880b0381a04c46617b7656e362585d52e9cf84a67e2009b749ff11`
- Build system: Autotools
- Conan reference: `ncurses/6.6`
- Third-party Conan prerequisites: none
- Final state: `built`; the package has not been uploaded by a release pipeline

## Package contract

- Build static wide-character libraries only. Shared ncurses libraries can shadow the
  platform `libncursesw.so.6` and are rejected by the recipe.
- Preserve all 86 entries declared by upstream `test/programs` and run the complete
  upstream `make -j1 check` target.
- Install public headers at the top-level include directory, all five static library
  components, the command-line tools, and the complete terminfo database.
- Export the CMake `FindCurses` contract, the Conan `ncurses::ncurses` target, and
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

All four patches apply through Conan patch-ng in each retained Conan build. The
original `config.guess` SHA-256 remains `50205cf...a7ef` after breaking the working
copy hardlink.

## Validation

Final validation uses one currently authorized HarmonyOS arm64 device and a fresh
Conan home. Upstream compilation and tests use `make -j1`. The test-package CMake
helper appends `-j1` after Conan's default job argument; GNU Make applies the final
job argument, and the compiler-process peak must remain one.

The device run must pass this stable contract:

- Upstream test/program entrypoints: 86/86
- Complete upstream `make -j1 check`: pass
- Terminfo database: 2899 entries reported by `tic`
- Added consumer workflows: 8/8
- Internal consumer assertions: 27/27
- Negative configurations: 2/2 (`shared=True` rejected and missing terminfo rejected)
- Build-system detection: `aarch64-unknown-linux-ohos`
- All six metadata linker traces selected only packaged static archives
- Packaged shared libraries: 0

The eight workflows are the two direct consumers plus `ncursesw6-config` and the
`formw`, `menuw`, `ncurses++w`, `ncursesw`, and `panelw` pkg-config consumers. The
recipe revision is `3dcfd3b6d759300e8997800cefe8c61f` and the package ID is
`21b17f8b2bc0e9511e276e3d57a23893067cefe5`.

The exact candidate HEAD/tree, authorized device, full package reference, project
archive, candidate manifest, runner, result archive, W3 log, and `.ci-result.json`
integrity value are intentionally not frozen in this committed file. The candidate
cannot contain its own commit hash, and ncurses terminfo output can change the Conan
package revision between otherwise equivalent builds. Those run-level values are
bound together after the final candidate is immutable, retained as a checksummed W3
closure, and copied into the PR validation section.

## Embedded finish/W3

The final retained run is acceptable only when the standard W3 step generates an
integrity-valid `.ci-result.json` with `exit_code=0` and every evidence-manifest hash
matches. If the outer `finish` command returns nonzero after W3 because of unrelated
repository-wide summary, knowledge, or legacy packaging-readiness checks, the PR must
report that result separately and must not describe the complete `finish` command as
passing.
