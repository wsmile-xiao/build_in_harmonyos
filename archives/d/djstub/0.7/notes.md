# djstub 0.7 HarmonyOS adaptation notes

## Scope

- Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2047
- Upstream: https://github.com/stsp/djstub
- Upstream tag: `0.7` (`228d837`)
- Build system: recursive Makefiles
- Package type: command-line tools (`djstubify`, `djlink`, `djstrip`, and `djelfextract`)

## Source and build analysis

The top-level Makefile builds `djstubify` with the native C compiler. Before that,
`mini/Makefile` invokes SmallerC (`smlrcc -dosp`) to generate the embedded DOS
loader `ministub.exe`; `ministub.S` then embeds that file into the native executable.
The alternative full stub needs `ia16-elf-gcc` and is not the maintained default.

Upstream has no `check` or other test target. The recipe therefore keeps the default
mini stub and adds a native functional smoke step: version reporting, stub generation,
and inspection. The consumer test performs an in-place add/remove round-trip and
compares the recovered ELF with the original packaged executable.

## Dependencies and W0 decision

- Required build tool: `smallerc/1.0.2`.
- Runtime shell/tools used by installed scripts: Bash plus GNU or LLVM binutils tools.
- Smaller C is adapted separately in PR #5117 and passed its single-package device
  shadow validation.
- Its transitive dependency `nasm/2.16.03` was merged in PR #5115 and is published
  in the `ohpcd` Conan remote for OHOS/armv8.

W0 is complete: `smallerc/1.0.2` is published in the `ohpcd` Conan remote. Per the
one-library/one-PR rule, no Smaller C or NASM files are included here; both resolve
from the dependency remote during official validation.

## HarmonyOS portability

`stubify.c` hard-codes `/tmp/djstub_XXXXXX` for in-place updates. The patch uses
`TMPDIR` when set and retains `/tmp` as the upstream-compatible fallback. This matches
the isolated worker requirement to use a per-run writable temporary directory.

Upstream exposes its version only through `-v`; the second patch also accepts
`--version`, which is the repository's L2 smoke-test contract for command-line tools.

HarmonyOS denies execution of scripts stored in the user data area even when their
shebang names the HNP Bash binary. The package therefore keeps the upstream Bash
scripts under `libexec/djstub/` and installs small native ELF launchers for `djlink`,
`djstrip`, and `djelfextract`. Each launcher invokes HNP Bash explicitly and prepends
`/data/service/hnp/bin` to `PATH` so the scripts can find LLVM binutils.

The platform also denied the upstream Makefile's external `install` command while
packaging. The Conan recipe copies the built program and scripts with Conan's native
file API instead of invoking that target.

The reusable noexec-script packaging pattern is recorded in
`knowledge/drafts/DRAFT-djstub-ohos-noexec-script-launcher.kv` and its companion Markdown draft.

## Validation status

- Official source URL and SHA256: verified locally.
- Source tree/build system: inspected.
- Both patches apply in order to the official 0.7 source archive.
- Both Conan recipes pass Python AST parsing; the archive files and directly related
  knowledge drafts are UTF-8 and LF-only.
- Local `conan inspect` and `conan export` passed with Conan 2.29.1.
- Full single-package device Shadow CI passed on 2026-08-12 using a fresh Conan home
  and the separately adapted Smallerc recipe in the isolated input archive.
- Tested commit: `575b61210465abb600c6440510e8200afcb23b0e`.
- Run root: `/storage/Users/currentUser/ohpc-ci-shadow/runs/575b61210465-20260812T092005Z-run-19186`.
- Input SHA256: `33c18a5f9548937c8cc6fc89997e7909693cdae77f1fee2961de73d765dc479b`.
- Runner completion: `status=pass`, `setup_rc=0`, `build_rc=0`.
- Gates: L0, L1, L2, L4, and L5 all passed; the package summary was 1/1 successful.
- The consumer test passed all 8 declared assertions, including version checks,
  stub add/inspect/remove with byte-for-byte recovery, and all three script entry
  points. The runner's generic L2 probe warns that `djlink` and `djstrip` do not
  implement conventional `--version`/`--help`; this is non-blocking and their actual
  supported invocations are covered by the consumer test.

Official PR CI #24359 passed on commit `4b782acc6d3616a75286626f23d6b01d31758f56`;
Conan resolved the published Smallerc dependency from the configured remote.

The package installs executables under `bin/`. The repository's L0k check will warn
when software-level `commands.json` is absent; the task constraint permits changes
only under this version directory, so no file was added outside `0.7/`.

## Next validation commands

Repeat the dependency-remote-only validation with the published Smallerc package:

```sh
conan download "smallerc/1.0.2" -r=ohpcd --only-recipe
CI_PACKAGES="archives/d/djstub/0.7" zsh ci/conan/build_and_test.sh
```

Single-package Shadow CI rerun:

```sh
/path/to/run-ohos-shadow-ci.sh archives/d/djstub/0.7
```

Expected test evidence includes `djstubify version 0.7`, `dj64 file format`, an
`aarch64/ELF` overlay line, a successful byte-for-byte round-trip, and `djlink -v`.
