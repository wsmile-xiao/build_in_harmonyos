# HarmonyOS device preflight: gcc-ada 9.5.0

- Issue: #2281
- Date: 2026-08-20
- Device: `currentUser@10.62.222.172:2222`
- Worktree: `feat/gcc-ada-9.5.0`

## Result

The isolated seed diagnostic passed on the real device:

- loader build run: `currentUser-gcc-ada-xpm-loader-build-r47-2281-20260820-233837-6001`, exit `0`;
- signed diagnostic loader SHA256: `c6868f79b7d16582210124124d148c816a12654af5bc87ceb455023e2512cf3f`;
- Ada preflight run: `currentUser-gcc-ada-xpm-loader-ada-r53-2281-20260820-235528-61246`, exit `0`;
- `seed_probe.o` was produced as an AArch64 relocatable ELF;
- `SHORT_NEEDED_DIAGNOSTIC=pass` was emitted.

The five GNAT frontend dependencies (`isl`, `mpc`, `mpfr`, `gmp`, and `z`)
were resolved from the short-name directory through `LD_LIBRARY_PATH` and
completed XPM mapping and relocation. The passing r53 setup deliberately does
not set `LD_PRELOAD`; an earlier preload-based variant made `gnat1` crash even
though a direct `gnat1 -v` smoke test passed.

## Scope and limits

This is a device-level bootstrap/loader preflight, not a completed Conan
package build. The r47 loader and short-name rewriting are diagnostic inputs
under the device job directory only; they are not copied into the gcc-ada
archive. `conan create`, full `all-gcc`/libgcc/libada, package installation,
and the consumer test still require a dedicated single-package device window.

## Next commands

```sh
python3 scripts/ohc-run.py conan-verify gcc-ada 9.5.0
CI_PACKAGES="archives/g/gcc-ada/9.5.0" zsh ci/conan/build_and_test.sh
```

Run the commands above only while holding the global device lock; classify the
first full-build failure before changing the recipe.
