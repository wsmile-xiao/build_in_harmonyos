# GCC

GNU Compiler Collection package for HarmonyOS PC. Version 9.5.0 is a
minimal native AArch64 C compiler build: it intentionally excludes C++,
bootstrap stages, multilib, sanitizers, OpenMP, quadmath and Graphite/ISL to
fit the package CI while retaining real compile, link and execution tests.

The recipe uses only GNU/GCC official source archives. No GitHub source is
used.

## 9.5.0.1 (all-PIE + LLD auto-signing)

`9.5.0.1` rebuilds the same gcc-9.5.0 source with a corrected toolchain
route.  The published 9.5.0 package links non-PIE host tools and target
objects; combined with the OHOS SDK LLD this triggers an AArch64
copy-relocation bug (misaligned LO12 literal loads for libc symbols such as
`stderr`) that crashes the built compiler's own test programs
(gcc.c-torture execute failures like nestfunc, printf-2, fprintf-2).

9.5.0.1 fixes this at the root:

- `--enable-default-pie` plus cleared `NO_PIE_*` makefile variables keep
  every host tool and target object position independent (no copy
  relocations).
- The OHOS SDK LLD is baked into the driver via `--with-ld`, replacing the
  GNU linker everywhere: LLD signs every ELF it links (`.codesign`), so the
  build, the installed driver and every program it links run on HarmonyOS
  without binary-sign-tool.
- Compiler wrappers shrink to thin search-prefix wrappers; the torture
  subset and `test_package` additionally assert the `.codesign` section to
  guard against unsigned-linker regressions.

See `9.5.0.1/notes.md` for the full engineering record.
