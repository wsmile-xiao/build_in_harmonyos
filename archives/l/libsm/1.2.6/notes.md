# libSM 1.2.6 adaptation notes

## Scope

- Dependency Issue: #1889, required by OpenJ9 0.59.0 Issue #1084.
- Official source: X.Org libSM 1.2.6 release tarball.
- The package is a library only; it does not install a command-line tool.

## Dependency gate

Fresh OHOS/AArch64 `--build=never` resolution proved that `xorgproto/2025.1`
and `xtrans/1.6.0` are published. The `libice/1.1.2` recipe is merged into
`origin/main`; its exact remote binary was not available at the last isolated
W0 check. Per the task owner's instruction, local downstream work uses the
merged recipe without claiming release publication. Remote CI remains paused
until the owner reports that network and build-timeout optimization is ready.

Upstream `configure.ac` requires `ice >= 1.1.0`, `xproto`, and xtrans whenever
optional libuuid support is unavailable. The recipe declares the exact current
dependencies and passes `--without-libuuid`, so build behavior cannot depend on
an undeclared system UUID library.
The package metadata propagates libICE and xorgproto to consumers because the
installed public SM headers expose ICE and X11 protocol types; xtrans remains a
private build requirement for the no-libuuid implementation path.

## Build design

The release archive includes generated Autotools files. The recipe does not run
autoreconf. Its only patch extends the bundled GNU config scripts to recognize
the native `aarch64-linux-ohos` triplet; it does not add platform-named C
preprocessor branches or substitute a GNU/Linux triplet. Documentation
generation is disabled to avoid unrelated DocBook tools.

The native target build follows the merged libICE recipe: it uses the Conan
profile compiler and dependency environment, a build-local writable `TMPDIR`,
`/system/bin/sh`, and serial make. It also replaces exactly two generated
`umask 077` sites with `umask 022` inside the isolated source copy, failing if
the generated configure contract changes. The installed `sm.pc` is rewritten
to use a package-relative prefix and the obsolete Libtool archive is removed.

AutotoolsDeps adds libICE to global `LIBS`, so even the initial executable
conftest links `libICE.so.6`. The target compiler linked that probe correctly,
but the loader initially failed with `Error loading shared library libICE.so.6`.
The build environment now derives `LD_LIBRARY_PATH` from the existing libdirs
of Conan host dependencies. This keeps configure and `make check` on the exact
Conan dependency graph without hard-coded cache paths or cross-build bypasses.

## Tests

Upstream registers no tests: the top-level `Makefile.am` contains only
`SUBDIRS=src doc`, and no source Makefile declares `TESTS`, `check_PROGRAMS`,
`check-local`, or another test target. `make -j1 check` remains mandatory and
the truthful upstream denominator is `0/0`.

The Conan consumer defines two independent target flows:

1. Round-trip the public client and manager error-handler registration APIs and
   verify the published protocol constants.
2. Allocate and release a complete multi-value `SmProp` and a reason-message
   vector through the public memory-management APIs.

The two executable results are the adapted-test denominator. Internal checks
are recorded separately and are not counted as test cases.

## Current state

Fresh W3 run `libsm-1.2.6-fresh-w3-r6` completed the shared and static Conan
builds from isolated homes. Both builds executed the mandatory zero-entry
upstream `make -j1 check` target and both installed-package consumers. The
independent result validator reported `upstream=0/0 adapted=2/2`; repeated
shared/static execution does not increase either denominator.

The shared package contains AArch64 `libSM.so.6.0.1` with SONAME `libSM.so.6`
and NEEDED `libICE.so.6`. The static package contains `libSM.a` with six unique
members. Both variants contain three public headers, relocatable `sm.pc`, the
license, and no Libtool `.la` file. The recipe is `built`, not published, and
no `.ci-result.json` was created manually.
