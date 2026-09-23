# cpp-httplib 0.41.0 Test Report

Date: 2026-09-11

## Source integrity and preflight

- Official tag: `yhirose/cpp-httplib` `v0.41.0`
- Tag commit: `073b58796205b928b61f4cae89ab4130b7f1aee0`
- Archive SHA-256: `6d38a6b74ea33ac3133b8352f2b55b557c1d42f36e1ed0c01f852e3218329d39`
- Header version: `CPPHTTPLIB_VERSION` is `0.41.0`
- Language preflight: PASS (`cpp`, CMake, 95% C++ source share)
- Read-only prescan: completed; findings were evaluated before build
- W0: GTest and curl recipes exist on `ohpcd`; target version does not

The delivery profile is dependency-free and disables optional TLS and
compression features. Its deterministic configuration therefore uses GTest
without the additional external-libcurl interoperability instance.

## Test-first baseline

Before the recipe existed, the explicit consumer command failed solely because
the reference was absent:

```text
conan test test_package cpp-httplib/0.41.0 --build=never -nr <profiles>
ERROR: Package 'cpp-httplib/0.41.0' not resolved: No remote defined.
```

## Upstream inventory

| Source | GoogleTest declarations | Official CMake target |
|---|---:|---|
| `test/test.cc` | 662 | yes |
| `test/test_proxy.cc` | 22 | no; external proxy topology |
| `test/test_thread_pool.cc` | 9 | no |
| `test/test_websocket_heartbeat.cc` | 5 | no |
| `test/test_benchmark.cc` | 2 | no; benchmark |
| Total | 700 | principal target only |

For the selected no-TLS/no-compression configuration, the official build
discovers 496 GoogleTest instances plus one fuzz CTest. Fifteen `_Online` tests
are excluded because they require external hosts. The deterministic total is
481 GoogleTest instances plus one fuzz test, 482.

On HarmonyOS CI, three tests share a relative pathname Unix socket fixture:
`UnixSocketTest.pathname`, `UnixSocketTest.PeerPid`, and
`UnixSocketTest.HostHeaderAutoSet`. Build #44435 showed all three failing from
the HMDFS-backed source working directory while `UnixSocketTest.abstract`
passed. This isolates the limitation to creation of pathname socket nodes on
HMDFS rather than AF_UNIX or cpp-httplib HTTP behavior. The updated OHOS recipe
will therefore exclude exactly those three entries and retain 479 deterministic
CTest entries; Linux retains all 482.

## Native Conan validation

Environment: Ubuntu WSL x86_64, GCC 13.3.0, Conan 2.29.1, CMake 4.4.3.

Result: PASS.

- Official archive download and SHA-256 verification: PASS
- Packaging patch application: PASS
- Upstream deterministic CTest: 482/482, 0 failed, 166.11 seconds in the
  final architecture-correction CI run
- `OpenStreamMalformedContentLength.OutOfRange`: 20/20 consecutive reruns
  passed after the upstream single-response fixture stabilization
- Package creation and upstream install: PASS
- Installed shape: one public header, four CMake files, README and MIT license
- Consumer: PASS

```text
CPP_HTTPLIB_CONSUMER_TEST_OK version=0.41.0 get=200 post=200
```

## HarmonyOS aarch64 validation

Release target: `os=OHOS`, `os.version=6.0`, `arch=armv8` (AArch64), Clang 15,
libc++, C++17. The local x86_64 machine is the cross-build host, not the target.

Result: PASS for the local AArch64 cross-build. Native execution remains
pending the post-fix remote CI run.

- Conan resolved the published OHOS armv8 GTest package.
- The official `httplib-test` and fuzz smoke target compiled and linked.
- The package installed the public header, CMake files, README and license.
- The portable and HarmonyOS-specific consumers compiled and linked.
- `llvm-readelf -h` identified all four executables as ELF64 AArch64.

Remote CI #44501 also established the following native target evidence before
the HarmonyOS-specific consumer was compiled:

- Official source verification and both patches: PASS.
- Official deterministic CTest: 479/479, 0 failed.
- Package installation: PASS.
- Failure: the test source incorrectly required `__x86_64__`, despite the
  official profile setting `arch=armv8`; this target/host mix-up is corrected
  to require `__aarch64__`/ARM64.
- Post-fix native CI result: pending fresh verification.

## Supplementary local x86_64 device validation

Target: `127.0.0.1:5555`

```text
Linux localhost 5.10.210 ... x86_64
emulator 6.0.0.48(SP31DEVC00E47R1P3)
```

This is supplementary API evidence only and is not the aarch64 release-target
acceptance result. Network runtime is limited by the production image's shell
policy.

- Official pure API subset: 101/101 passed across 38 suites.
- Official fuzz smoke: PASS (`Execution finished`).
- HarmonyOS-specific consumer: PASS.

```text
HARMONYOS_CPP_HTTPLIB_TEST_OK arch=x86_64 kernel=5.10.210 version=0.41.0
```

The device is an undebuggable production image. HDC `smode` returns
`Cannot set root run mode in undebuggable version`. The shell context is
`u:r:sh:s0` under SELinux enforcing. A standalone system-call probe produced:

```text
socket_fd=4
bind_result=-1 errno=13 Permission denied
```

The same EACCES is observed by the portable consumer and by all official tests
that bind TCP or Unix sockets. Because this is a device execution-domain
restriction, not a cpp-httplib result, no library patch or silent test skip was
introduced. Full loopback HTTP behavior remains covered by the native 482/482
suite and the native Conan consumer.

## Repository verification

Targeted package CI: PASS.

- L0 quality gates: PASS
- Knowledge graph integrity/quality: PASS (540 entries)
- PR-diff junk check: PASS; the current branch also carries the no-curl CI
  pre-downloader repair required by build #44413, which must be separated from
  the package PR to satisfy W2 before merge.
- Official source download, SHA-256 verification and patch application: PASS
- Conan create, upstream CTest and consumer execution: PASS
- Destructive negative test proving the consumer depends on the package: PASS
- Patch safety and package artifact checks: PASS

The first remote CI run (`PR #9577`, build `#44413`) stopped before Conan could
build the package: the worker did not provide the external `curl` executable,
and Conan's subsequent direct GitHub download timed out. The shared
pre-downloader now falls back to Python's standard-library HTTP client when
`curl` is absent, while `conandata.yml` continues to contain only the official
GitHub source required by PF7. The Python child download has the same bounded
total-time behavior as the curl path. Regression coverage verifies timeout,
three retries, URL failover, incomplete-file cleanup and the `file://` rewrite.
A real mirror download also reproduced the locked archive SHA-256 above.

The second remote CI run (build `#44435`) downloaded and compiled successfully,
then passed 479 of 482 deterministic CTest entries. Its only failures were the
three tests using `./httplib-server.sock`; the abstract-address AF_UNIX test and
all other entries passed. The recipe now expresses that OHOS/HMDFS capability
boundary as an exact-name CTest exclusion and reports the platform-excluded
count separately instead of weakening or patching library behavior.

The third remote CI run (build `#44482`) stopped in `source()` before
configuration because a post-generation whitespace cleanup had removed the
unified diff's required blank context markers; Conan reported
`patch stream is incomplete`. The exact auto-generated patch artifacts were
restored byte-for-byte. A fresh Conan `source()` run then downloaded and
verified the official archive, extracted it, parsed both patches and applied
both patches successfully.

The fourth remote CI run (build `#44501`) used the repository-standard
OHOS/armv8 profile. It passed all 479 configured upstream tests, packaged and
installed cpp-httplib, then failed while compiling `harmonyos_test.cpp` because
that test incorrectly required `__x86_64__`. The local VM architecture had
been confused with the release target. The test now requires AArch64 and checks
an `aarch64`/`arm64` runtime machine name; the post-fix remote result remains
pending.

During final native verification, upstream
`OpenStreamMalformedContentLength.OutOfRange` reproduced an independent race:
five targeted reruns passed and the sixth failed. The v0.41.0 helper read only
one request fragment before sending and closing, so unread request data could
make the kernel reset the connection and discard the response. The generated
test-only patch backports the upstream mainline fix that consumes the complete
HTTP headers first. The subsequent full 482-test run and 20 consecutive
targeted reruns passed.

The mandatory `finish cpp-httplib 0.41.0 built` path was executed. Its earlier
local run covered the x86_64 supplementary configuration; it is not presented
as aarch64 acceptance. The generic finish wrapper
returned partial because its separate legacy checks assume an in-tree source
tarball, a precompiled `packaging/` tarball and the CI-only aarch64 compiler at
`/data/service/hnp/bin/clang`; it also reports pre-existing repository knowledge
entries E219, E253 and E305. These checks are not an aarch64 Conan W3 result and
were not bypassed with hand-written marker files.

Repository regression result: 9/11 suites passed, matching the pre-port
baseline. The two unchanged failures are:

1. `test_v1220.py` uses the CI-only Git path
   `/data/service/hnp/git.org/git_2.45.2/bin/git`, which does not exist on the
   Windows host.
2. `test_v1221.py` expects the baseline recipe catalog to contain the
   `headeronly` and `copy` classifiers; classifier behavior itself passes.

Neither baseline failure was masked. The framework change in this revision is
limited to the pre-download transport fallback and its focused regression test.
