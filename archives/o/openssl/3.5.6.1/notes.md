# OpenSSL 3.5.6.1 OHOS adaptation notes

## Scope

- Conan reference: `openssl/3.5.6.1`
- Upstream source: OpenSSL 3.5.6
- Target: OHOS armv8
- Delivery: static PIC `libssl.a` and `libcrypto.a`, headers, and OpenSSL CLI
- Third-party Conan dependencies: none

The `.1` suffix is an OHOS recipe revision. It does not claim a new upstream
OpenSSL release. The source is the official codeload archive for tag
`openssl-3.5.6`, with an explicit `.tar.gz` filename and SHA256
`a572efd967f99e2dc8228c46ba45410948d5b9a343f1e0271b9960298982866b`.

## Failure reproduced from the downstream curl build

The published `openssl/3.5.6` archive contains this unresolved symbol:

```text
libdefault-lib-rand_unix.o U __fd_chk
```

Linking that static archive into shared libcurl fails in `rand_unix.c`. Object
disassembly places the relocation immediately after OpenSSL checks that the
random-device descriptor is below `FD_SETSIZE`, clears an `fd_set`, and enters
the `FD_SET` operation. The current OHOS SDK does not provide `__fd_chk` in its
target libraries, so adding a downstream shim would hide an invalid dependency.

OpenSSL's default `--with-rand-seed=os` enables both `getrandom` and the
`DEVRANDOM_WAIT` fallback. This recipe selects the supported kernel entropy
source explicitly with `--with-rand-seed=getrandom`, which excludes the
`DEVRANDOM_WAIT`/`select`/`FD_SET` code while retaining cryptographic entropy.
No private symbol shim is used. Two refresh-generated portability patches route
the remaining upstream `FD_SET` call used by CLI/test code through OpenSSL's
bounded helper. On musl, where the checked `FD_SET` macro introduces the
unavailable private symbol, the helper uses musl's exposed `fd_set.fds_bits`
layout after rejecting negative and out-of-range descriptors. Other libc
implementations retain their native `FD_SET` macro. The
reusable entropy diagnosis and verification pattern is recorded in E220
(`archives/knowledge/graph/draft/E220-draft-CX17.kv` and
`archives/knowledge/graph/draft/E220-draft-CX17.md`).

## Toolchain and package policy

OpenSSL uses a custom Perl `Configure` system rather than Conan's CMake or Meson
abstractions. On Windows build hosts the recipe derives the SDK `native/sysroot`
and LLVM tools from `tools.build:compiler_executables`, then binds Clang to
`aarch64-linux-ohos`. Native OHOS workers retain their configured compiler.

`Configure` records the compiler and binutils commands verbatim in its generated
Makefile. The recipe therefore keeps Windows SDK tool paths quoted before
configuration. This is required for `install_dev`, which calls `RANLIB` inside a
`/usr/bin/sh` loop: an unquoted `DevEco Studio` path is split at the space and
fails as `D:/tool/harmony/DevEco: No such file or directory`. Earlier archive
rules append `|| echo Never mind` to `RANLIB`, so a build log can mask the same
path error until installation; the final `install_sw` exit status and installed
archives must both be checked.

The configure prefix is the target-side root (`/`), `OPENSSLDIR` is `/ssl`, and
the target library directory is the absolute `/lib`. OpenSSL derives
`ENGINESDIR=/lib/engines-3` and `MODULESDIR=/lib/ossl-modules` from that target
path. Using a relative `lib` with the root prefix produces `//lib/...` in the
generated configuration, so the recipe also excludes `--libdir=` from MSYS
argument conversion. Packaging uses `DESTDIR=<Conan package folder>`, so the
AArch64 archives and CLI do not embed the Windows Conan cache directory.
Upstream CMake/pkg-config files are removed because Conan supplies relocatable
consumer metadata.

The package is static-only because `libssl` and `libcrypto` can collide with
system library names. `-fPIC` keeps the archives usable by shared downstream
libraries. `no-asm` follows E006 and avoids architecture-specific crypto
assembly defects. OpenSSL still installs the dynamic `legacy.so` provider when
only `no-shared` is selected, so this recipe also uses the official
`no-legacy` and `no-module` options. The package step also removes the provider
directory to prevent a reused package folder from retaining a stale module
from an earlier build. The default provider, RAND, SHA-256, and TLS APIs
required by curl remain enabled, while the package contains no OpenSSL shared
objects.

## Validation contract

The recipe builds OpenSSL software and all upstream test programs. It runs the
upstream test suite only when Conan reports that target binaries are runnable.
The Conan consumer calls `RAND_bytes`, not only hashing or TLS initialization,
so it pulls the exact entropy backend that exposed `__fd_chk`.

Before submission, validation must confirm:

1. a forced source `conan create` succeeds;
2. `llvm-nm -u libcrypto.a` contains no `__fd_chk`;
3. the real `RAND_bytes` consumer links as AArch64 ELF;
4. static archives are PIC and no shared OpenSSL libraries are packaged; and
5. `install_sw` completes without a split SDK tool path; and
6. `openssl version -a` reports `/ssl`, `/lib/engines-3`, and
   `/lib/ossl-modules` exactly; and
7. target execution covers the C API consumer plus CLI version, SHA-256, and
   random-generation checks.

## Verified forced build and target run

The final v41 `conan create --build=openssl/*` used a new build folder and
completed with the following evidence:

- recipe revision: `8717e485e00723b4b2fece557d5623fd`;
- package ID: `f23d5a9b1d537641c03c7814478a2fadb727650a`;
- package revision: `e5e3fe1944e9ce718ed1a8f8ac5efeee`;
- build log SHA256:
  `F08A9EA67021D45850D3893DCB691628A0A8B173D5FBD9679C044802AA039DFE`;
- package contents: 149 files, two `.a` archives, no `.so`, no upstream
  `.cmake`, and no `.pc` files;
- `llvm-nm -u` found zero `__fd_chk` references in both `libcrypto.a` and the
  packaged OpenSSL CLI;
- the packaged CLI and the RAND/SHA-256/TLS consumer are ELF64 AArch64, and
  the consumer linked successfully; and
- the CLI embeds `OPENSSLDIR=/ssl`, `ENGINESDIR=/lib/engines-3`, and
  `MODULESDIR=/lib/ossl-modules`, with no `//lib/` or Windows user path.

The upstream surface contains 344 Perl recipe files and 250 direct `test/*.c`
sources; OpenSSL generated 339 program targets, all of which completed the
cross-build. Conan correctly reported `can_run=false`, so it did not execute
AArch64 programs on the Windows host.

The final CLI and C consumer were then uploaded to their final HMDFS paths on a
HarmonyOS HongMeng Kernel 1.12.0 aarch64 device. Their pre-signing SHA256 values
matched the local files, and both ELF files were signed in place. The C consumer
passed version, `RAND_bytes`, SHA-256, and TLS context checks (4/4). The CLI
passed version, three exact configured paths, the fixed SHA-256 of `abc`, and
16-byte random generation checks (6/6). The target result is 10/10 assertions,
100%.

## Contest paths

- **Path B**: archived E220 generalizes the `__fd_chk` failure into a reusable
  method for selecting an OHOS-supported OpenSSL entropy backend and verifying
  the archive through the real RAND consumer path.
- **Path C**: OpenSSL combines a custom Perl toolchain, optional hand-written
  assembly, provider and entropy subsystems, a security-sensitive static link
  boundary, and a large upstream test suite. The failure appears only when a
  downstream shared library pulls `rand_unix.o`, which the previous smoke test
  did not do. These properties create both adaptation and validation barriers.

## Review follow-up: SHA-256 known-answer assertion

The consumer originally checked only that `SHA256()` returned its output
buffer. That proved API success but not digest correctness. The test now
compares the digest of `OpenSSL OHOS consumer` against the fixed expected
SHA-256 value with `CRYPTO_memcmp`.

The updated consumer was cross-compiled and linked against the cached package,
then transferred to a HarmonyOS HongMeng Kernel 1.12.0 aarch64 device. Its
pre-signing SHA256 was
`DE6660D39DC0692DE9D4B544C95E5C436569AF178323797208400A1595151959`.
After in-place HMDFS signing, the C consumer again passed version,
`RAND_bytes`, the fixed SHA-256 known-answer test, and TLS context creation.
The CLI checks also passed, preserving the 10/10 target result.

## Review follow-up: libc guard and POSIX shell

The portability helper is now guarded by `__MUSL__`, which the Windows-to-OHOS
recipe defines together with the target and sysroot. This is deliberately not
applied to every POSIX libc: POSIX specifies the `fd_set` type and the
`FD_SET`/`FD_ZERO` operations, but does not standardize an `fds_bits` member.
The current OpenHarmony SDK header exposes `fds_bits` and implements `FD_SET`
through the unavailable `__fd_chk`; other libc implementations retain their
native `FD_SET` path. The helper checks both bounds before writing the known
musl layout.

The CLI test now uses `#!/bin/sh` and `set -eu`, matching the Conan invocation.
Each configured-path assertion ends with `grep`, so POSIX pipeline status is
the assertion status and `set -e` propagates a mismatch. A negative test with
the correct OpenSSL version but three wrong configured paths exited 1.

The v43 forced build completed all software and upstream test-program
cross-compilation, installation, and Conan package creation before the outer
60-minute runner timed out during the initial `test_package` CMake configure.
The resulting package is `openssl/3.5.6.1#d871951ad035e2c4eecb6112af441801`
with package revision `7eb284013aae2afe5ceb5d54836c3b5f`. A separate
`conan test` against that exact cached package then configured, compiled, and
linked the real consumer and exited 0.

The rebuilt package still contains 149 files, two static archives, and no
shared objects. `llvm-nm -u` found zero `__fd_chk` references in both
`libcrypto.a` and the CLI. The new consumer and CLI are AArch64 ELF files with
pre-signing SHA256 values
`8F914B1AB43C8C14F58549BA04595DAE0708360115C44173D019AB4FA9505F34`
and
`EF124E1252DD74A321BDACF6EC65A3A4CA37266727942412F216DB3EDD5C6AD1`.
After transfer and in-place signing on HarmonyOS PC, the C API checks passed
4/4 and the CLI checks passed 6/6, preserving the 10/10 target result.
