# GCC Ada bootstrap seed analysis

## Candidate comparison

| Candidate | Result |
| --- | --- |
| Existing `gcc/9.5.0` Conan package | C frontend only; no `gnat1` or GNAT tools |
| OpenHarmony cmd-pkgs | No GNAT entry |
| Alire-provided GNAT | Official documentation limits Linux hosts to x86-64 |
| GNAT-FSF-builds native AArch64 Linux | Available only in much newer GCC series; regular Linux/glibc build |
| Alpine 3.12 AArch64 GCC/GNAT 9.3 | Selected: older GCC, AArch64, musl, official signed distro packages |

## Selected package set

All URLs and SHA256 values are in `conandata.yml`.

| Package | Purpose |
| --- | --- |
| `gcc-9.3.0-r2.apk` | GCC driver, C frontend, collect2, seed GCC support files |
| `gcc-gnat-9.3.0-r2.apk` | GNAT tools, `gnat1`, Ada include and ALI/static runtime files |
| `libgnat-9.3.0-r2.apk` | Completes distribution Ada runtime links |
| `libgcc-9.3.0-r2.apk` | Seed unwind/runtime shared library |
| `isl-0.18-r0.apk` | `libisl.so.15` for `gnat1`/`cc1` |
| `mpc1-1.1.0-r1.apk` | `libmpc.so.3` |
| `mpfr4-4.0.2-r4.apk` | `libmpfr.so.6` |
| `gmp-6.2.1-r1.apk` | `libgmp.so.10` |
| `zlib-1.2.12-r3.apk` | `libz.so.1` |

## ELF evidence

Local ELF64 parsing of the downloaded AArch64 files found:

| File | Interpreter | `DT_NEEDED` |
| --- | --- | --- |
| `gnat`, `gnatmake`, `gnatbind`, `gnatlink` | `/lib/ld-musl-aarch64.so.1` | `libc.musl-aarch64.so.1` |
| `gcc`, `collect2` | `/lib/ld-musl-aarch64.so.1` | `libc.musl-aarch64.so.1` |
| `gnat1` | `/lib/ld-musl-aarch64.so.1` | isl, mpc, mpfr, gmp, zlib, musl |
| `libgnat-9.so` | n/a | `libgcc_s.so.1`, musl |

All inspected files use ELF machine 183 (AArch64) and no RPATH/RUNPATH was
present. The recipe therefore supplies private `lib/` and `usr/lib/` search
paths only for the seed process.

## Trust and package boundary

The recipe verifies every archive before extraction, rejects unsafe archive
paths, handles APKv2 concatenated gzip members directly, materializes links
inside the seed root, signs ELF copies, and validates required files before
use. The seed is a compiler bootstrap input comparable to the repository's
official Go/Zig distributions. It is not exposed through package metadata and
is absent from final artifacts.

The first device gate must still prove executable compatibility. This report
does not treat ELF header compatibility as equivalent to successful execution.
