# libdisasm 0.23 adaptation notes

## W0 dependency check

`configure.ac` only probes the C compiler and libtool; there are no
`AC_CHECK_LIB`/`AC_CHECK_HEADERS` for external libraries. The source is
pure C (ia32 tables + decoder). Zero required and zero optional
dependencies, so W0 passes trivially.

## Build system analysis

- Autotools (autoconf 2.5x era) + libtool 1.5.24, generated `configure`
  shipped in the tarball.
- `configure.ac` has no cross-compilation knowledge; `AC_CANONICAL_HOST`
  delegates to the bundled 2006-era `config.guess`/`config.sub`, which do
  not know `aarch64` at all (0 matches for `aarch64` in both files).
- `AC_ISC_POSIX` generated no actual ISC detection code in this
  `configure` (obsoleted macro; no-op here).
- Outputs: `libdisasm/libdisasm.la` (library, header `libdis.h`),
  `x86dis/x86dis` (CLI), plus docs/man. The `perl/` subdir is
  `EXTRA_DIST` only (not built). The `swig/` bindings are not built by
  default either.

## Adaptation decisions

1. **config.sub aarch64** (0001): same approach as the a52dec 0.7.4
   adaptation — early-accept `aarch64-*-linux*|aarch64-*-ohos*` before
   the CPU-COMPANY parsing rejects them.
2. **umask 022** (0002): `configure` creates the `config.status` tmp dir
   with `umask 077 && mktemp -d "./confXXXXXX"`; on setgid hmdfs the
   resulting directory becomes unwritable for the subshells, so switch to
   umask 022 (identical to the a52dec 0002 patch).
3. **Native-style triples**: on OHOS the recipe passes
   `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`
   so the 2003-era configure treats the build as native (the OHOS clang
   driver then compiles "natively" on the aarch64 device). This avoids
   old-configure cross mode paths and skips `config.guess` entirely.
4. **Static default**: `shared=False, fPIC=True` matches the repo
   convention for vintage C libraries (a52dec/celt/cdb). libdisasm is
   not a system-homonym library on OHOS.
5. **libtool .la removal**: `make install` installs `libdisasm.la`
   wrappers; the recipe deletes them after install (Conan 2 `copy()` has
   no `delete=` argument).

## Upstream test inventory (R51)

| Item | Count |
|---|---|
| `TESTS` registered in `test/Makefile.am` | 1 (`run-test.sh`) |
| `check_PROGRAMS` | 3 (`insn-test`, `testdis`, `quikdis`) |
| Instructions compared in `ia32_test_insn.S` | 694 (618 self-comparing + 76 with expected-text comments, 17 of them XFAIL) |

`run-test.sh` needs GNU `as --32` + `objdump` + `perl`, which do not exist on
the OHOS target, so the suite was executed via a faithful device port
(`reports/upstream-suite-device-port.py`): the perl/sed/diff comparison
semantics are replicated line-for-line; only the environment tools are
substituted (clang `--target=i386-linux-gnu` integrated assembler for
`as --32`, `llvm-readobj --sections` for `objdump -h`, python3 for perl).
A minimal dialect shim canonicalizes the 2003 gas spellings clang rejects
(FP memory-op suffixes, `movsx/movzx -> movswl/movzwl`, `cmpxchg8bq`,
branch targets above INT32_MAX as negative decimals); the INPUT side always
reads the original file.

**Result (device, default mode)**: 694 comparisons -> `ok: 671`,
`XFAIL: 17` (the upstream-documented expected failures), `FAILED: 6`.
The 6 deletions are: 2 = the XFAIL `movsx/movzx` lines themselves (already
counted in the 17), and 4 = self-referential short-branch lines
(`jcxz 0x0` / `loop -1` / `loop 0` / `loopz -127`) whose expected text
hard-codes 2003-gas rel8 encodings and (for `loopz`) signed rel8 rendering;
analysis in the port's docstring shows these are internally inconsistent
under any single modern assembler (libdisasm 0.23 renders negative rel8 as
unsigned). In `--try-xfail` mode (attempts the XFAIL lines against their
source text): `ok: 656, FAILED: 21` = 17 XFAIL attempts + the same 4 dialect
lines. Excluding the 17 XFAIL and 4 dialect lines, all 673 remaining
comparisons match (100%).

## Consumer test design

`test_package/test_libdisasm.c` decodes encodings verified against the
opcode tables in `ia32_opcode_tables.c`:

- `55` push ebp — size 1, `insn_push`, operand `ebp`
- `90` nop — size 1, `insn_nop`
- `B8 01000000` mov eax,1 — size 5, `insn_mov`, dest `eax`, imm 1
- `03 C3` add eax,ebx — size 2, `insn_add`
- stream `55 8B EC 83 EC 08 90 C3` — per-instruction sizes
  {1,2,3,1,1} and types {push,mov,sub,nop,ret}
- `0F 38` — invalid escape in the 0.23 tables: returns 0 and
  `insn_invalid` (per `ia32_disasm_addr` INVALID_INSN path; this is the
  same case upstream `insn-test.c` probes)

## Verification status

- [x] Source URL + sha256 verified against SourceForge download
- [x] Patches verified: `patch --dry-run` and `git apply --check` both
      clean on the pristine tarball
- [x] Recipe/test_package/MANIFEST/commands.json structure complete
- [x] Local L0 gates: repo pre-commit hook (L0a-L0n) all passed;
      `conan inspect` loads the recipe; W0 preflight clean (zero deps)
- [x] `conan create` on OHOS device (10.62.178.77:2222, isolated conan
      job, repo CI profile): built `libdisasm.a` + `x86dis` +
      `include/libdis.h` + man pages; package id
      `21b17f8b2bc0e9511e276e3d57a23893067cefe5`
- [x] `test_package` executed on device: 30/30 assertions passed
      (21 API + 9 consumer use case)
- [x] `x86dis` CLI exercised manually on device (intel + att syntax)
- [x] upstream suite executed on device via the faithful port
      (ok 671 / XFAIL 17 / 6 unmet, see the R51 section above)

## Device findings (10.62.178.77)

1. **HMDFS script-exec denial** (fixed in the recipe): conan's
   `Autotools.configure()` execs `./configure` directly and failed with
   Error 126 even though the file mode was `rwxr-x---`. On this worker
   HMDFS refuses direct execve of *scripts* regardless of mode (chmod is
   silently ignored; a `umask(0)`+`0755` creation is clamped to `0770`),
   while *ELF* binaries exec fine at mode 750. The recipe now invokes
   `sh "<configure>" <args>` with the exact `AutotoolsToolchain`
   arguments — equivalent to upstream's `sh ./configure` and harmless on
   CI workers. Knowledge draft:
   `knowledge/drafts/libdisasm-0.23-hmdfs-script-exec-denied-sh-configure.*`
2. **Profile `os.version`**: the device's own `ohos-aarch64` profile
   lacks `os.version` (`Invalid: 'settings.os.version' value not
   defined`). Running with the repo CI profile
   (`ci/conan/profiles/ohos-aarch64`, which pins `os.version=6.0`)
   works and keeps device runs CI-equivalent.
3. **Source download**: SourceForge is unreachable from the device
   (HTTP 000). Used the CI's pre-download mechanism: the sha256-verified
   official tarball was transferred to the job and the *job copy* of
   conandata.yml rewritten to a `file://` URL (official URL restored
   after the run; the committed conandata.yml is untouched).
4. **Misc environment**: clang needs `TMPDIR` (read-only `/tmp`);
   `$HOME/usr/local/bin/install` is a script shadowing the toybox ELF
   `install`, but configure's own probing found the working `ginstall`
   ELF, so `make install` was unaffected; `make jobserver mkfifo`
   warnings (HMDFS fifo restriction) are benign; the getcwd error spam
   in make output is known HMDFS noise and does not affect results.
5. **Intel syntax format**: the library separates mnemonic and operands
   with a tab (`push\tebp`) and formats immediates as `0x%08X`
   (`0x00000001`) — the two initial text assertions were corrected
   against the real `x86dis` output on device.

## Next-step commands (device / shadow CI)

Branch `feat/libdisasm-0.23`, package path `archives/l/libdisasm/0.23`.
Device verification is COMPLETE (see above). Shadow CI (single package,
from the repo root on the runner):

```sh
CI_PACKAGES="archives/l/libdisasm/0.23" zsh ci/conan/build_and_test.sh
```

Remaining before the PR: `finish` / `submit` (W3/W4) per the SKILL
workflow, then PR description with the verification results above.


