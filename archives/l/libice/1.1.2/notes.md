# libice 1.1.2 adaptation notes

## Scope

- Dependency Issue: #1840, required by OpenJ9 0.59.0 Issue #1084.
- Official source: X.Org libICE 1.1.2 release tarball.
- The package is a library only; it does not install a command-line tool.

## Dependency gate

Fresh OHOS/AArch64 `--build=never` resolution proved that
`xorgproto/2025.1` and `xtrans/1.6.0` are published. The recipe declares both
exact references because upstream `configure.ac` requires the `xproto` and
`xtrans` pkg-config modules. The xtrans host requirement is private because
its transport sources are compiled into libICE and are not exposed by the
installed headers or `ice.pc`; xorgproto remains the public Conan requirement.

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
the obsolete non-relocatable Libtool archive is removed. The upstream libICE
ABI versioning is preserved.

## Tests

Upstream has no registered tests: the top-level `Makefile.am` contains only
`SUBDIRS = doc specs src`, and no source Makefile declares `TESTS`,
`check_PROGRAMS`, `check-local`, or another test target. `make check` is still
executed and the truthful upstream count is `0/0`.

The Conan consumer adds two independent flows:

1. Write and read a complete `IceAuthFileEntry` through the public authority
   file API, compare every field, verify EOF handling, and clean the file.
2. Verify `ICEAUTHORITY` path resolution, generate a nonempty 32-byte magic
   cookie, and round-trip the public error-handler registration API.

The two process results are the test denominator. Their 18 internal checks are
recorded separately and are not counted as test cases.

## Current state

Fresh W3 run `libice-1.1.2-fresh-w3-r11` completed the shared and static Conan
builds, both mandatory `make -j1 check` invocations, both installed-package
consumer flows, package inspection, and independent result validation. The
validated result is `upstream=0/0 adapted=2/2`; repeated shared/static execution
does not increase either test denominator. The recipe is marked `built` pending
PR CI and release publication. No `.ci-result.json` is created manually.
---

**编译结束**: 2026-08-06 02:23
**最终状态**: built
