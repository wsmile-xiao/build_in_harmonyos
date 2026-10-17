# recode 3.7.15 OpenHarmony PC adaptation

## Source and build

- Source: upstream Git tag `v3.7.15`, downloaded from the GitHub API.
- The tag is a Git tree rather than a generated release archive, so the recipe
  also downloads gnulib commit `eecd8afd696055cf39ef934208724bfe850c5760`.
- `bootstrap` regenerates `configure`, Makefiles, and the gnulib sources before
  the Conan Autotools cross build.
- The recipe disables NLS and compiler-warning promotion; it keeps the recode
  CLI and `librecode` library enabled.
- HarmonyOS uses Conan `libiconv/1.17` for the charset conversions exercised by
  the upstream suite. Automake, Libtool, gettext, and m4 are build
  requirements because the target image lacks the complete bootstrap toolchain.

## OpenHarmony-specific handling

The generated configure script creates a private temporary directory with
`umask 077`. HMDFS build directories can reject that mode, so the recipe
changes the generated script to use `umask 022` before configuring. This is a
build-environment workaround and does not alter recode conversion behavior.

The upstream `tables.py` generator reads `iconv -l` through `os.popen()`. On
the HarmonyOS Python 3.12 runtime, that path raises `TypeError: underlying
read() should have returned a bytes-like object, not 'str'`. The recipe keeps
the upstream parser and captures the command output in a regular temporary
file under `TMPDIR`, avoiding the incompatible Python pipe reader.
The `libiconv/1.17` package provides the required `bin/iconv` executable but
does not add that directory to the build worker's `PATH`. The generated code
therefore invokes the dependency's absolute package path, so the fix covers
both the HarmonyOS pipe incompatibility and the minimal CI worker environment.

## Validation boundary

The test package compiles a consumer of `recode_new_outer`,
`recode_new_request`, and `recode_string_to_buffer`. Cross compilation proves
the headers, library, and consumer link; it does not prove target execution
when no HarmonyOS PC device is attached.

Packaging uses `install-exec` because the cross-built `recode` binary cannot
run under `help2man` to generate the man page during a target package build.

## HarmonyOS PC device test

- 2026-08-27: Rebuilt the package with `conan create` on a HarmonyOS PC
  AArch64 target. The package build and Conan consumer test both completed
  successfully.
- The generated test Makefile points to a host Python and the target Python
  Cython extension was not available. Therefore the unmodified upstream test
  modules and `pytest` harness were run with a device-only `Recode.py` facade
  that invokes the final packaged `recode` CLI. The facade and deployment
  files are not part of this PR.
- The original failure `t70_inferenz.py/test_1` now passes with the packaged
  binary. The complete `tests/t*.py` run passed 496 of 496 tests, including
  `t40_java.py` and `t90_bigauto.py`.
- Formal Conan log SHA256:
  `9e18111278c68f12b2a48aa9b64befef137718bc7f97da6919abcc4f1526489a`.
- Targeted test log SHA256:
  `ce49700288645805c19819a976a0b24c1616e1db8a42c4458cc31d3d5c82916d`.
- Full upstream test log SHA256:
  `041440e2b3e58ac8521e32cb6c6682b575d636f208f0fc0835e9d6d527f90dba`.
- Final packaged `recode` SHA256:
  `6cd78210728b7f0b3bf1c99de9afe0dca2ad74d20385dd5ad0c0eb805e748a10`.
- Final packaged `librecode.so.3.7.15` SHA256:
  `7f260cc4a5343c15eaaffdd785660944cabd88861eca349c49f42744269bd20d`.
- These results cover the formal package build, consumer test, and target
  execution. CI, review, merge, and remote publication remain separate gates.

## Knowledge extension draft

- Added `knowledge/drafts/E337-draft-2301.kv` and
  `knowledge/drafts/E337-draft-2301.md`.
- The draft generalizes the reproducible bootstrap pattern for Autotools Git
  snapshots that require a pinned gnulib revision and declared bootstrap tools.
- Existing E007, E011/E223, E041, and E058 entries remain related boundaries;
  E337 is not promoted to a formal entry until this PR is reviewed and merged.
