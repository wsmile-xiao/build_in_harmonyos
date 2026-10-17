# W0 report: gcc-ada 9.5.0

- Issue: #2281
- Date: 2026-08-20
- Intended role: native HarmonyOS/AArch64 GNAT compiler for Ada libraries such
  as adacgi 1.6.

## Conan dependency checks

The checks used Conan 2.29.1, a fresh isolated cache, the `ohpcd` remote, and
the required `conan download --only-recipe` operation.

| Reference | Result |
| --- | --- |
| `gcc/9.5.0` | downloaded revision `a19319bfdbeeec7f210cfdd11733fa7b` |
| `gnat/9.5.0` | unavailable; exact download exited 1 |
| `gcc-ada/9.5.0` | unavailable; exact download exited 1 |
| `gcc-ada-bootstrap/9.5.0` | unavailable; exact download exited 1 |
| `gcc-ada-bootstrap/5.4.0` | unavailable; exact download exited 1 |

The official cmd-pkgs index also has no GNAT entry, and the local Windows host
has no GNAT or WSL distribution.

## Bootstrap resolution

The absence of a Conan package does not require an undeclared system compiler.
The repository already accepts checksum-pinned official binary compiler
distributions as recipe source inputs for Go and Zig. The selected GNAT seed
is Alpine Linux 3.12 `main/aarch64` GCC/GNAT 9.3.0-r2:

- official authoritative repository URL;
- AArch64 ELF and musl interpreter compatible with the target execution model;
- older than GCC 9.5, as GCC recommends for a GNAT bootstrap;
- package metadata and nine archive SHA256 values recorded;
- used only during `conan create`, never copied to the final package.

The seed minimum closure is the GCC and GNAT APKs, libgnat/libgcc, and the five
shared libraries loaded by `gnat1`. Unrelated GCC D/OpenMP links found in the
distribution package are deliberately not included.

## Device preflight

The authorized device preflight passed the signed Alpine GNAT seed compile:
`seed_probe.o` was produced and the run emitted
`SHORT_NEEDED_DIAGNOSTIC=pass` (run
`currentUser-gcc-ada-xpm-loader-ada-r53-2281-20260820-235528-61246`).
This validates the bootstrap executable closure and short-name dependency
resolution in the isolated loader diagnostic.

## Decision

Proceed to an isolated full device build when a single-package window is
assigned. W0 dependency and seed-compile uncertainty are resolved; full GCC
build, libada build, package installation, and the consumer test remain
unverified on OHOS/AArch64.
