# libfs 1.0.10 adaptation notes

## Scope

- New adaptation for HarmonyOS PC (OHOS aarch64). No previous libfs archive
  exists in this repository.
- Official source: X.Org libFS 1.0.10 release tarball.
- The package is a library only; it does not install a command-line tool.

## Dependency gate

Fresh OHOS/AArch64 `--build=never` resolution proved that
`xorgproto/2025.1` and `xtrans/1.6.0` are published. The recipe declares both
exact references because upstream `configure.ac` requires the `xproto` and
`xtrans` pkg-config modules. The xtrans host requirement is private because
its transport sources are compiled into libFS and are not exposed by the
installed headers or `libfs.pc`; xorgproto remains the public Conan
requirement.

## Build design

The release archive includes generated Autotools files. The recipe therefore
does not run autoreconf. Its only source patch extends the bundled GNU config
scripts to recognize the native `aarch64-linux-ohos` triplet; it does not
introduce platform-named C preprocessor branches or substitute a GNU/Linux
triplet. Documentation generation is disabled so the library build does not
pull DocBook tooling.

The build uses the compiler declared by the Conan profile and binds a writable
build-local `TMPDIR`. On OHOS, each configure, make, check, and install command
loads the generated Conan build environment and then overrides `SHELL` and
`CONFIG_SHELL` with `/system/bin/sh`. This avoids the HNP Bash `getcwd` failure
inside HMDFS Conan build folders while retaining all generated compiler and
dependency variables. The recipe also uses `/system/bin/mkdir -p` for the
Autotools `MKDIR_P` capability. Before configure, it requires exactly two
upstream `umask 077` sites and changes them to `umask 022` in the isolated
build copy. This prevents `config.status` from creating an HMDFS temporary
directory that its effective user cannot write, while failing closed if the
upstream script layout changes. Every make invocation remains serial.
The installed pkg-config file is rewritten to package-relative paths, while
the obsolete non-relocatable Libtool archive is removed. The upstream libFS
ABI versioning is preserved.

## Tests

Upstream ships exactly one test program: `test/Makefile.am` declares
`noinst_PROGRAMS = FSGetErrorText` (top-level `SUBDIRS = src test`), and the
generated `test/Makefile.in` carries the same `noinst_PROGRAMS` entry with no
`TESTS` or `check_PROGRAMS`, so the Automake `check` target builds the binary
but executes nothing. The recipe still runs `make -j1 check` (builds the
program, proves the test sources compile) and then executes the built
`test/FSGetErrorText` for real. OHOS ships no xfs font server, so the recipe
starts an in-process loopback peer that answers the minimal FS protocol
handshake needed by the test's single `FSOpenServer()` call (fsConnSetup with
status=AuthSuccess, then fsConnSetupAccept with a 32-bit aligned vendor
string) and drains the connection afterwards. The test itself only reads
`ext_procs` from the server handle and resolves the 16 error-string lookups
(13 named FS error codes plus 3 out-of-range values) locally, so no further
server replies are required. The upstream test sources are used unmodified
and the verified result is `upstream=1/1`.

The Conan consumer adds two independent flows:

1. Offline public-API contract (`test_package/api_contract.c`, helper
   `libfs_api_contract`): `FSMalloc`/`FSFree` round trip, `FSServerName`
   precedence for the three documented input shapes (explicit server wins,
   `FONTSERVER` fallback, `NULL` when unset), the `NULL` contracts of
   `FSFree` and the list destructors, and the documented `NULL` failure
   return of `FSOpenServer` for a missing server, an unknown transport, and
   an unreachable `FONTSERVER` endpoint — every flow is asserted
   deterministically, never on a connection succeeding.
2. OHOS target-artifact contract (recipe-side checks in `test()`): the
   installed shared `libFS.so` is ELF64 AArch64 `DYN` with
   `SONAME` = `libFS.so.6`, bare `DT_NEEDED` sonames including the musl
   libc, no `DT_RPATH`/`DT_RUNPATH`, exported `FSOpenServer`,
   `FSServerName`, `FSMalloc`, `FSFree` symbols; the consumer binary is
   ELF64 AArch64, dynamically linked against `libFS.so.6` in shared mode,
   and carries exactly one `.codesign` section after signing; in static mode
   `libFS.a` members are ELF64 AArch64 objects defining the same entry
   points. Both helper executions use an explicit `self.run()`.

The two consumer flows plus the upstream FSGetErrorText program form the test
denominator (3 cases: 1 upstream, 1 new integration, 1 HarmonyOS-specific).
The 31 internal checks of the consumer flows are recorded separately and are
not counted as test cases; the upstream test owns its 16 internal lookups.

## Current state

Fresh local run on `feat/libfs-1.0.10` completed the shared and static Conan
builds (`-pr:h ohos-aarch64 -pr:b ohos-aarch64`), both mandatory
`make -j1 check` invocations plus real execution of the built upstream
`test/FSGetErrorText` against the recipe's in-process FS handshake peer,
both installed-package consumer flows, package
inspection, and independent result validation. The validated result is
`upstream=1/1 integration=1/1 harmonyos_specific=1/1, 3 cases after
adaptation`; repeated shared/static execution does not
increase any test denominator. Cross-compile note: configure requires
`--disable-malloc0returnsnull` because `XORG_CHECK_MALLOC_ZERO`'s auto
branch runs a conftest binary; the root cause and the Conan
`configure_args` instance pitfall are recorded as
`knowledge/drafts/DRAFT-libfs-xorg-malloc0-cross-probe` (path B, dedup
checked against E029/E210/E476 and the rpl_malloc draft). The recipe is
marked `built` pending PR CI and release publication. No `.ci-result.json`
is created manually.

---

**编译结束**: 2026-09-17 12:25
**最终状态**: built
