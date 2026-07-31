# EditorConfig Core C 0.12.9 HarmonyOS PC notes

## Scope

- Conan reference: `editorconfig/0.12.9`.
- Upstream core commit: `e082c947e7f7b14240195d55c060a6e1eda1b0a1`.
- The tag pins `tests` to gitlink commit
  `5ca0b296dc31124d0303895c163013450bd97958`; the release tag archive omits
  submodule content, so the recipe fetches that exact official test archive.
- Delivery includes the shared C library, public headers, pkg-config metadata,
  and the `editorconfig` CLI.

## Dependencies

The only third-party Conan dependency is `pcre2/10.45`. Its recipe revision
`5ecd2f9871deb549e2ae07489f2e40df` was verified with
`conan download --only-recipe -r=ohpcd` before adaptation.

## Build decisions

The historical archive forced a static CLI to hide a relative-library loading
problem and carried a generated `configure` wrapper solely for an obsolete
clean-verify path. The Conan recipe now uses the upstream CMake project
directly, links the CLI to `libeditorconfig.so.0`, and writes the final
`$ORIGIN/../lib` RUNPATH during the initial link so a Windows cross-install
does not need to relink an OHOS ELF file.

The package removes the always-built static archive and the upstream CMake
export that referenced it. The installed `editorconfig.pc` uses
`prefix=${pcfiledir}/../..` so metadata remains relocatable.

The old `src/lib/misc.c` patch treated `__OHOS__` as UNIX. It remains absent:
the recipe now supplies the upstream platform contract as the OHOS-only CMake
compiler definition `-DUNIX` through Conan's CMake toolchain definitions. This
keeps platform selection in the build configuration, preserves CMake's
configuration-specific flags, and avoids adding a source-level `__OHOS__`
branch.

Buildbot #10246 showed that native HarmonyOS CMake reports the platform as
unknown and does not provide the uppercase `UNIX` preprocessor definition.
Both shared and static builds therefore reached the upstream
`#error "Either UNIX or WIN32 must be defined."`. Adding a toolchain
preprocessor definition fixes the precise missing contract without replacing
CMake's default optimization or build-type flags; current-head CI remains the
authoritative validation for this remediation.

Buildbot #11256 (build ID 11861, raw log ID 68383) then completed all 15 source
build targets and executed the full 197-case upstream suite. It reported
177 passes and 20 failures, all of them `_ML` cases. Their actual output was
correct; CMake 4.1's `PASS_REGULAR_EXPRESSION` evaluation did not match the
anchored expression across output lines. Two test-portability patches now pass
the original anchored expression into `ec_sort.cmake`, normalize CRLF/CR/LF to
an ASCII record separator in both actual and expected values, and perform the
strict match inside the script. The script first preserves the upstream
trailing-newline trim, then reconstructs the logical output emitted by
`message()` with exactly one final newline before matching. No test is skipped
and no expected value is relaxed. The trailing-newline-sensitive
`meta_multiline` case passes, while a deliberately wrong extra line still
fails.

## Verification boundary

The Windows-to-OHOS build proves source reproducibility, AArch64 ELF
generation, upstream CTest registration, package metadata, RUNPATH, and real
consumer linking. Buildbot #11256 proves that all 197 upstream cases executed
on HarmonyOS before the fix; 177 passed and 20 correct multiline outputs were
rejected by the test harness. The fix has positive and negative CMake 4.1
regression checks, but 197/197 remains pending current-head CI. A HarmonyOS PC
executed the four added unit cases and parser consumer from the fixed recipe:
5/5 passed.

## Validation

The fixed Windows-to-OHOS `conan create --build=editorconfig/*` completed all
15 Ninja steps. Both declared patches applied with zero fuzz. CMake found the
pinned PCRE2 binary, enabled the official test tree, and registered all 197
upstream CTest cases. Generated test definitions contain 20 `EXPECTED_REGEX`
script arguments for the multiline cases and no multiline
`PASS_REGULAR_EXPRESSION` property. The package step installed the shared
library and CLI, removed the static archive and stale upstream CMake export,
and rewrote `editorconfig.pc` to `prefix=${pcfiledir}/../..`.

The generated Ninja rules were inspected directly after the CI remediation.
Every EditorConfig compile rule contains `-DUNIX`, while the OHOS toolchain's
Release flags still contain `-O2 -DNDEBUG`; the fix therefore supplies the
missing upstream platform contract without replacing CMake's default flags.

The real Conan consumer compiled and linked an AArch64 executable that calls
`editorconfig_get_version`, creates a handle, parses a real `.editorconfig`
file, validates returned properties, and destroys the handle. It was not run
by the Windows cross-build because `can_run=false`; it was later signed and
executed successfully on an AArch64 HarmonyOS PC.
The current forced build includes this consumer compilation and has SHA256
`0BF37F365A89D88FD31A0886BFE0D9784EB2755229E27310A2BE0746FD67200F`.

Four independent CTest unit cases now add 25 assertions for the public version
API, handle version mutation, custom config filenames, and relative-path error
reporting. The unit executable and existing consumer both completed OHOS
AArch64 compilation/linking. The fixed `conan create --build=editorconfig/*`
log SHA256 is
`0BF37F365A89D88FD31A0886BFE0D9784EB2755229E27310A2BE0746FD67200F`;
all four unit cases and the consumer passed on the target device (5/5).

Direct artifact checks found:

- `libeditorconfig.so.0.12.9` is ELF64 AArch64 with SONAME
  `libeditorconfig.so.0`, RUNPATH `$ORIGIN/../lib`, and only `libc.so` in
  `NEEDED`;
- the CLI is ELF64 AArch64 with RUNPATH `$ORIGIN/../lib` and only
  `libeditorconfig.so.0` plus `libc.so` in `NEEDED`;
- all three installed shared-library names have SHA256
  `52AD2BB4D1082C22E5E06646B03683B8706FFEE5EE5A974ED21FD0756348950E`;
- the package contains 10 files, two public headers, one CLI, no static archive,
  no upstream CMake export, and no Windows path hit.

Conan produced recipe revision `7343448bcf3e287d7038f6022ad5846a`, package
ID `0d16c3b585cf3487cd8947eff7f5d5c7b1caf4c7`, and package revision
`52f929b61306c38f615d2f1ccee9a6b7`. The complete build log is
`C:\Users\cxy\Documents\Codex\.tmp\editorconfig-pr3072-ci-fix-conan-create-20260730-v2.log`
with SHA256
`0BF37F365A89D88FD31A0886BFE0D9784EB2755229E27310A2BE0746FD67200F`.

On 2026-07-29, the two test executables and `libeditorconfig.so.0` were
transferred to their final HMDFS paths, verified byte-for-byte by SHA256,
signed in place, and executed with the package directory in `LD_LIBRARY_PATH`.
The four unit modes (`version`, `handle_version`, `conf_filename`, and
`relative_path_error`) and the parser consumer all passed. The device log
SHA256 is
`6947EDEE418AA72B197EA47B119740839AC75FE1D3F256F120F27B0573296676`.

On 2026-07-30, the same five modes were repeated with the executables and
library from recipe revision `7343448bcf3e287d7038f6022ad5846a`. All three
files matched their local SHA256 values before final-path signing, and 5/5
tests passed. The new device log SHA256 is
`CE071E13F3B19F13DE49F3F26D6679E968A4D5C3E0141EE8E7D5CCF0E325D8A0`;
the archived report is `reports/device-test-20260730-ci-fix.md`.

## Knowledge decision

Formal project knowledge E150 already covers release/tag archives that omit
git submodules and the need to fetch the submodule source separately. The
explicit codeload filename and Windows-to-OHOS CMake RUNPATH handling also
reuse existing local knowledge. The CMake 4.1 multiline-regex failure is
recorded in the operator's global local knowledge for future diagnosis, but
this PR does not add a project knowledge deliverable. This dependency remains
path A and does not claim path B or path C.

W5 graph validation reproduced four existing baseline errors in E213/E214 and
12 existing index warnings. This branch does not modify those entries or the
knowledge index, so the result is recorded without expanding the dependency
PR into unrelated knowledge maintenance.
