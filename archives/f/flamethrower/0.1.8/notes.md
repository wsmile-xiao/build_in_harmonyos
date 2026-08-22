# Flamethrower 0.1.8 Adaptation Notes

## Source Identity

- Task: OHPCD contrib task 130, `flamethrower/0.1.8`
- Claimer: `2301_80739235`
- Task branch: `feat/flamethrower-0.1.8`
- Real upstream source: Debian source package `flamethrower_0.1.8-7.dsc`
- Orig tarball: `https://deb.debian.org/debian/pool/main/f/flamethrower/flamethrower_0.1.8.orig.tar.gz`
- Orig SHA256: `c816afb109be5b3e28bb7b7fa1c120827c7f85852e0e996755ddee94c780c6d2`

This task is the old Debian/SystemImager Perl multicast utility. It must not be
substituted with the unrelated DNS-OARC C++ project named `flamethrower`.

## Language And Build Contract

The source is an architecture-independent Perl application:

- `bin/flamethrower`
- `bin/flamethrowerd`
- `lib/Flamethrower.pm`
- `Makefile.PL`
- configuration and init-script assets under `etc/`

There is no C or C++ source in the real 0.1.8 upstream archive. The Conan
package type is therefore `application`; it installs relocatable wrapper scripts
under `bin/` and the original Perl entrypoints under `libexec/flamethrower/bin/`.

## Dependencies

Runtime dependencies identified from source and Debian metadata:

- `perl/5.42.2`
- `appconfig/1.71.1`
- `udpcast/20250223`

`udpcast/20250223` has already passed isolated OHOS/arm64 W0. `appconfig/1.71.1`
is the selected AppConfig revision from dependency task 3322 and PR #4886. Its
fresh isolated OHOS/arm64 W0 passed on 2026-08-20 with RREV
`b4f7385c654fecb3a40368d55098efb2`, PID
`6b129b068851896169fae42d399fa922d239ce8a`, PREV
`22d56edbe712df210d34ee35a661dc0e`, `binary_remote=ohpcd`, and
`info_invalid=null`. The Flamethrower root W0 may now resume from a new
isolated Conan home.
`--build=never`.

Debian patch 0007 introduced `use File::Which` only for the `udp-sender`
command vector. The local 0008 patch removes that extra runtime dependency and
keeps the existing `Flamethrower->which($file, $ENV{PATH})` preflight plus
Perl's list-form PATH lookup for `udp-sender`.

## Patches

The recipe carries the Debian 0.1.8-7 patch set:

- default loopback configuration
- documentation typo fixes
- CVE-2008-5141 temporary-file fix
- init script runlevel and init-functions fixes
- MakeMaker DESTDIR support
- udpcast child-stop fixes

Local patch 0008 narrows the Debian udpcast-stop patch by removing the
unneeded `File::Which` import and correcting the global TTL argv from
`" --ttl"` to `"--ttl"`. No patch uses an OHOS-named conditional macro.

Local patch 0009 replaces the inaccessible `/usr/lib/flamethrower` Perl module
path with the package-provided `FLAMETHROWER_LIBDIR` path. The target wrapper
sets this variable before invoking the real Perl entrypoint.

Local patch 0010 treats the optional `debug` configuration as disabled when
AppConfig returns an undefined value. This prevents the daemon's valid
non-debug path from passing an undefined value to `lc`.

Local patch 0011 registers `debug` in `Flamethrower->read_config`. Without an
explicit definition, AppConfig emits `debug: no such variable` before 0010 can
test the returned value. The variable inherits the existing empty default, so
an omitted setting is quiet and remains disabled.

## Tests

The upstream 0.1.8 archive has no official test suite:

- no `t/` or `test/` directory
- no `make test` implementation beyond default MakeMaker behavior
- no independent upstream test script

The local `test_package` scaffold registers one consumer smoke test. It checks
that the packaged wrapper scripts can report versions, that wrappers export
`PERL5LIB`/`FLAMETHROWER_LIBDIR`, that the packaged module and libexec layout are
usable, that `Flamethrower` can parse a sample configuration through
`AppConfig`, and that udpcast tools are present on `PATH`. It also includes
target-side positive and negative paths for daemon configuration parsing without
starting a real udpcast transfer. The positive daemon path must produce an empty
log when the optional debug setting is omitted. Internal checks in that script are assertions
inside one consumer test and must not be counted as separate test cases.

## Current Status

AppConfig/1.71.1 publication and the fresh Flamethrower root W0 are closed.
Exact recipe revision, package ID, package revision, host-consumer result, and
formal target W3 identity are maintained in external hash-bound task evidence.
They must be rebound whenever a committable package file changes.

The recipe tree deliberately does not self-record the current W3 endpoint or
run ID: editing those values after a run would change the candidate and make
that same run stale. The formal W3 contract instead requires one launch,
runner exit code 0, all consumer markers, zero-byte test stderr, and an
independent readback proving the exact task root was removed. W4, W5, PR, CI,
review, submission, and publication remain separate gates and are not implied
by these adaptation notes.
---

**编译结束**: 2026-08-21 17:47
**最终状态**: built
