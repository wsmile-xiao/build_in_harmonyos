# OpenSSL 4.0.1 OHOS adaptation notes

## Scope

- Conan reference: `openssl/4.0.1`
- Upstream source: OpenSSL 4.0.1 (official GitHub release tarball)
- Target: OHOS armv8 (clang 15.0.4, musl)
- Delivery: static PIC `libssl.a` and `libcrypto.a`, headers, and OpenSSL CLI
- Third-party Conan dependencies: none (Perl is a build-time tool taken from PATH)

## Upstream 4.0.1 vs 3.5.6 — what changed for the build

Verified against the actual 4.0.1 source tree:

1. **Build system is still the Perl `Configure`** (capital C). There is no
   top-level `CMakeLists.txt`; the experimental CMake exporter mentioned in
   NEWS.md only installs generated CMake config files from the Perl build.
   The recipe therefore keeps the `linux-aarch64` target and the same
   Configure/make flow as the 3.5.6.1 baseline recipe.
2. **Engines are removed upstream.** `engines/` no longer exists; the
   `no-engine` option and `OPENSSL_NO_ENGINE` are always present, and the
   generated Makefile has **no `ENGINESDIR`** variable anymore (only
   `OPENSSLDIR` and `MODULESDIR`). `install_sw` is now
   `install_dev install_modules install_runtime` (no `install_engines`).
3. **New `no-pinshared` option.** Static builds still pin shared libraries by
   default (`-z nodelete`-style linker flags); `no-shared` does *not* imply
   `no-pinshared`. The recipe passes both so a downstream shared library that
   statically links libcrypto is not pinned unintentionally.
4. **QUIC is enabled by default** (`quic` is not in the default-disabled list;
   only `hqinterop` demo is disabled by default).
5. **`max_per_call = 500` and the `mkbuildinf.pl` template lines are
   unchanged** in `Configurations/unix-Makefile.tmpl` / `crypto/build.info`,
   so the two OHOS source preparations from the 3.5.6.1 recipe still apply.
6. **`linux-aarch64` target verified present** (`Configurations/10-main.conf`,
   `perl ./Configure list` shows it).

## Patch portability from 3.5.6.1 (verified one by one)

Both 3.5.6.1 patches fail `patch -p1 --dry-run` on 4.0.1 because the
surrounding context changed upstream (SM2_SECONDS/FFDH_SECONDS defines were
removed around `apps/speed.c:25`; `BIO_printf`→`BIO_puts` near the async wait
loop; `include/internal/sockets.h` gained VXWORKS/TANDEM branches which shifted
the `openssl_fdset` block down). The underlying problems still exist in
4.0.1, so both patches were **regenerated against the 4.0.1 tree** rather than
dropped:

- `apps/speed.c:1565` still uses a raw `FD_SET(job_fd, &waitfdset)` — the only
  remaining raw FD_SET in `apps/` (all other 30 call sites upstream already
  use `openssl_fdset`). Patch 0001 reroutes it through the helper and adds the
  `internal/sockets.h` include.
- `include/internal/sockets.h` still defines `openssl_fdset` as the raw
  `FD_SET` macro on non-Windows, which on musl expands to the checked macro
  referencing the libc-private `__fd_chk` symbol. Patch 0002 implements the
  helper with musl's exposed `fds_bits` layout under an `__MUSL__` guard,
  rejecting out-of-range descriptors before writing.

Verified on-device: compiling a minimal `FD_SET` program with the device clang
(musl native) leaves `U __fd_chk` in `nm -u`, i.e. the checked macro is still
what musl headers produce. The current OHOS SDK 26.0.0.18 sysroot `libc.a`
does provide `__fd_chk` (in `fortify.o`) so links succeed today, but the
helper keeps the package independent from that SDK-private detail — the exact
dependency that broke downstream libcurl linking in the 3.5.6 era (E220).

`--with-rand-seed=getrandom` is kept from the baseline recipe: it excludes
the `DEVRANDOM_WAIT`/`select`/`FD_SET` seeding path from `libcrypto` entirely
(verified: 0 `__fd_chk` references in `libcrypto.a`/`libssl.a` even without
patches), so the patches only matter for CLI/test code.

## Parallel-make hazard (re-verified on 4.0.1)

An exploratory `make -j8 build_sw build_tests` on this HMDFS-backed workspace
failed once with `mv: bad 'crypto/bn/libcrypto-lib-bn_const.d.tmp': No such
file or directory` — the same object was compiled twice concurrently and one
job's dependency file disappeared under the other. A re-run completed
(MAKE_EXIT=0). This is why the recipe builds with `-j1`, matching the
baseline; the `max_per_call = 500 → 100` Makefile-template reduction from the
baseline recipe is likewise retained.

## Toolchain and package policy

Same policy as the 3.5.6.1 baseline: static-only packaging (`libssl`/
`libcrypto` collide with system library names, R26), `-fPIC` so downstream
shared libraries can use the archives, `no-asm` (E006), `no-legacy`,
`no-module`, `no-docs`, plus the new `no-pinshared` (see above). The
configure prefix is the target-side root `/`, `OPENSSLDIR=/ssl`, target lib
dir `/lib`; 4.0.1 derives `MODULESDIR=/lib/ossl-modules` from that. The
package step removes upstream `cmake`/`pkgconfig` metadata and the empty
`ossl-modules` directory; Conan supplies relocatable consumer metadata.

## Validation contract

The recipe builds OpenSSL software and all upstream test programs
(`build_sw build_tests`) and runs the upstream test suite only when Conan
reports that target binaries are runnable (`can_run`). On the cross profile
`can_run` is false, so upstream test programs are compiled and linked only —
target-side execution requires `can_run=true` (staged below for follow-up).

The Conan consumer calls `RAND_bytes` (pulls the real entropy backend),
checks the fixed SHA-256 known answer with `CRYPTO_memcmp`, and creates a
`SSL_CTX` via `TLS_method()`. The CLI script asserts `OpenSSL 4.0.1`,
`OPENSSLDIR: "/ssl"`, `MODULESDIR: "/lib/ossl-modules"`, the fixed SHA-256 of
`abc`, and 16-byte random hex output. Note: OpenSSL 4.0 removed engines, so
the 3.x-era `ENGINESDIR` assertion is intentionally absent.

## Build results

The forced `conan create . --user=ohpcd --channel=stable -pr:h/-pr:b
ohos-aarch64 --build=missing` completed with EXIT=0 on the second run after
adding `-D__MUSL__` to the OHOS compiler command (see "Patch guard activation"
below).

- Full package reference:
  `openssl/4.0.1@ohpcd/stable#d809a2a0f270e2e0af2388b6556faedb:f23d5a9b1d537641c03c7814478a2fadb727650a#09d752bc5aa4deedb47d07197f6947ba`
- Package contents: 150 files, two static archives (`libcrypto.a`,
  `libssl.a`), one CLI binary, no `.so`, no upstream `.cmake`, no `.pc`
- `llvm-nm -u`: **zero `__fd_chk` references** in `libcrypto.a`,
  `libssl.a`, the CLI, and all apps objects (`libapps-lib-apps.o`,
  `libapps-lib-s_socket.o`, `openssl-bin-speed.o`, `openssl-bin-s_client.o`)
- CLI embedded paths: `OPENSSLDIR: "/ssl"`, `MODULESDIR: "/lib/ossl-modules"`,
  no ENGINESDIR (removed in 4.0)
- Upstream test suite ran in-place (`can_run=true` on the aarch64 OHOS device):
  `Files=363, Tests=4079, Result: PASS` — 309 scripts ok, 53 skipped
  (FIPS-only/Windows-only/enable-tfo/rc5/LMS/legacy-PBE/ACVP etc. — all
  build-option-related, none musl/OHOS-specific), 0 FAILED
- test_package: C consumer (`RAND_bytes` + fixed SHA-256 known answer via
  `CRYPTO_memcmp` + `SSL_CTX_new(TLS_method())`) passed; CLI script
  (version/paths/SHA-256/random) passed
- On-device CLI run: `openssl version -a` reports `OpenSSL 4.0.1 9 Jun 2026`,
  `OPENSSLDIR: "/ssl"`, `MODULESDIR: "/lib/ossl-modules"`,
  `Seeding source: getrandom-syscall`; `dgst -sha256` of `abc` matches the
  expected digest; `rand -hex 16` produces 32 hex chars

## Patch guard activation (second-run fix)

The first `conan create` run already passed all tests but left one
`U __fd_chk` reference in the CLI: the OHOS SDK clang does **not** predefine
`__MUSL__` (it predefines `__OHOS__`/`__OHOS_FAMILY__` only), and the baseline
recipe only injected `-D__MUSL__` on the Windows cross path. The
`__MUSL__`-guarded helper in `internal/sockets.h` therefore fell back to the
raw `FD_SET` macro, which on musl expands to the checked macro referencing
libc-private `__fd_chk`. The fix defines `-D__MUSL__` in the OHOS build
environment too (verified in the build log compile lines), after which every
`__fd_chk` reference in the produced CLI and objects is gone. This keeps the
package free of the SDK-private fortify symbol that broke downstream libcurl
linking in the 3.5.6 era (E220), independent of whether the target SDK libc
happens to provide it.
---

**编译结束**: 2026-09-03 13:21
**最终状态**: built
