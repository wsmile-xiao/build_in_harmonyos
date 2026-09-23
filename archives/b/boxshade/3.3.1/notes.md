# boxshade 3.3.1 HarmonyOS (OpenHarmony PC) adaptation notes

## Status

- Branch: `feat/boxshade-3.3.1`
- Issue: none found in the target repository for boxshade.
- Current state: recipe authored; verified on two tracks —
  1. Windows-host OHOS aarch64 cross build: compiler + link + packaging + ELF checks pass;
  2. OHOS device CI (PR 8460): source download, make build, link, ELF self-sign, packaging
     and test_package execution all pass on the real device. The only CI failure was the
     smoke test's string assertion (`-help` does not print the literal "BOXSHADE"; it
     prints "Allowed command line parameters are:") — fixed by matching the real help
     output.

## Upstream source note

The task upstream URL `https://github.com/boxshade/boxshade` does not exist
(GitHub API returns 404; the GitHub user `Boxshade` has no public repositories),
so the authoritative **3.3.1** source was taken from the Debian pool orig tarball
(the same authoritative-mirror pattern as `crasm/1.11`):

- URL: https://deb.debian.org/debian/pool/main/b/boxshade/boxshade_3.3.1.orig.tar.gz
- SHA256: `bf21eeecd0c4b1fc2299854091825fb082818ed779fb7a7ac98a9994f19445b1`
- Content: classic 1997 BOXSHADE 3.3 C version (C port v3.31 by Hartmut Schirmer;
  header states "completely public-domain").

> **Conan-data URL scheme note (updated 2026-09-06)**: during the first CI runs on
> 2026-09-05 the OHOS worker had neither `curl` nor a working Python SSL module, so
> an `https://` source URL failed conan's download ("Can't connect to HTTPS URL
> because the SSL module is not available") and the recipe temporarily used the
> identical file over plain http (same SHA256 verified). Per the maintainer-triggered
> AI review on PR 8460 (repo rule: source URLs must be HTTPS), the recipe now uses
> the official `https://deb.debian.org/...` URL again; the sha256 is unchanged.

## W0 Dependency Check

- Runtime/build dependencies: none beyond the C toolchain and libc.
- Conan dependencies: none.
- Dependency split requirement: not applicable.

## Source and Build Analysis

- Build system: plain Makefile only — upstream ships `makefile.unx` (and DOS/Windows
  variants `makefile.bcc/.djp/.w16`); there is **no default Makefile**, no configure,
  no install and no test target.
- Main binary: `boxshade` (built in the source root).
- Runtime data files: `box_dna.*`, `box_pep.*`, `clust160.*`, `positive.*`, `strong.*`
  (`*.par` parameter sets, `*.grp` similarity groups, `*.sim` default similarity
  files). Lookup order in `ask()`: current directory, then `$BOXDIR`, and
  `get_logical("BOXDIR")` falls back to the **executable's directory**
  (`bx_misc.c`, `save_binpath`). => package the data files in `bin/` next to the
  binary so the CLI is self-contained.
- Upstream tests: none (no test suite / no `make check`).

## Recipe Notes

- Build obtains the C compiler from `tools.build:compiler_executables` and runs
  `make -f makefile.unx -j1 CC=... CFLAGS=... LDFLAGS=... LIBS=""` (R9, R33).
- OHOS cross/device flags: `--target=aarch64-linux-ohos` (arch armv8) and
  `--sysroot=...` are injected from the recipe when provided by the profile conf;
  device linker `-fuse-ld=/data/service/hnp/bin/ld.bfd` is added when present.
- `LIBS=""` is passed on purpose: the musl-based OHOS libc satisfies the code, and
  the tarball's default `-lm` is not required for the build.
- The package installs `bin/boxshade` + `bin/*.par|*.sim|*.grp` (data files).
- On OHOS devices the recipe self-signs the built/packaged executable with
  `/data/service/hnp/bin/binary-sign-tool` when available (same helper as
  `crasm/1.11`), enabling execve of the ELF.
- `test_package` runs the packaged CLI with `-help` and checks its output contains
  `Allowed command line parameters are:` (verified executing the signed ELF on the
  OHOS device; upstream has no functional test suite to port).

## Local Preflight Results (Windows host, cross to OHOS aarch64)

- Environment: DevEco Studio HarmonyOS 26 SDK native clang 15.0.4 (aarch64-linux-ohos
  target), sysroot via `C:\Users\13909\ohos-sysroot`, OHOS-adapted Conan 2.29.1.
- Manual cross compile+link of all 14 upstream C files
  (`clang --target=aarch64-linux-ohos --sysroot=... -std=gnu89 -O2`):
  succeeded; `llvm-readobj --file-headers` reports `elf64-littleaarch64 / aarch64`,
  `main` present.
- Key finding: without `-std=gnu89`, `bx_read.c` fails with
  "call to undeclared function 'gets'" + int-to-pointer error (pre-C99 code);
  all other units warn. `-std=gnu89` makes the whole tree compile cleanly.
- Full `conan create` with `-pr:h=ohos-aarch64-windows -pr:b=default`:
  recipe export, fetch of the Debian orig tarball, make build and packaging all
  passed; packaged `bin/boxshade` re-checked as aarch64 OHOS ELF.

## Verification Commands

```sh
# Local (Windows host -> OHOS target), Windows-variant profile:
python -m conans.conan create archives/b/boxshade/3.3.1 \
  --name=boxshade --version=3.3.1 -pr:h=ohos-aarch64-windows -pr:b=default --build=missing

# Device CI (as run by the PR pipeline):
conan create archives/b/boxshade/3.3.1 --user=ohpcd --channel=stable \
  -pr:h=$HOME/.conan2/profiles/ohos -pr:b=$HOME/.conan2/profiles/ohos --build=missing
```
