# dc3dd 7.3.1 adaptation notes

## Current status

- Stage: W0-W4 complete for the buildable file-imaging package. Shadow CI r4
  passed build, package, and `test_package`; the upstream hashing and
  file-imaging scripts also passed on the aarch64 device.
- Target: `aarch64-unknown-linux-ohos`.
- Build system: Autotools with a pre-generated `configure`.
- Dependencies: none; the release contains the required gnulib sources.
- Source archive: official SourceForge ZIP, SHA256
  `bd1b66d20a4020ab94b512e56d76cb5f86470d0216081586d596366927cb8d8b`.
- Device: `currentUser@10.62.178.77:2222`.

## Source and build audit

The official 7.3.1 download is `dc3dd-7.3.1.zip`. The upstream README
mentions `autoconf-1.10.1` and `gperf`, but the release already contains
`configure`, `Makefile.in`, and generated build helpers. No bootstrap step or
separate Conan dependency is required for the normal release build.

The top-level `Makefile.am` builds `lib`, `src`, `man`, and `po`; the upstream
functional shell tests under `tests/` are not part of the default `SUBDIRS`.
`make check` therefore does not cover the imaging and hashing scenarios. The
consumer test package provides a small deterministic subset, while the full
upstream scripts remain a device-only follow-up.

The OHOS SDK clang target defines both `__OHOS__` and `__linux__`. The OHOS
sysroot supplies the Linux-compatible headers used by the default non-hdparm
path, so no source-level C patch is needed for the regular-file path.

## Adaptation changes

1. `0001-config.guess-ohos.patch`
   - Recognizes `HarmonyOS` and emits `<machine>-unknown-linux-ohos`.
   - Changes the temporary-directory probe from `umask 077` to `umask 027`,
     preserving group access for the HMDFS workspace without world access.
2. `0002-config.sub-ohos.patch`
   - Accepts and preserves the `linux-ohos` operating-system component.
3. `0003-configure-umask.patch`
   - Applies the same HMDFS-safe umask to the generated Autoconf checks and
     `config.status` template.
4. `0004-freadahead-musl.patch`
   - Adds the musl-like opaque-`FILE` fallback used by HarmonyOS for
     `freadahead`, returning no buffered-byte count without dereferencing
     private libc fields.
5. `0005-freadptr-musl.patch`
   - Adds the matching opaque-`FILE` fallback for `freadptr`.
6. `0006-freadseek-musl.patch`
   - Makes the unreachable opaque-`FILE` pointer increment path a harmless
     no-op instead of an `abort()` placeholder.
7. `0007-fseterr-ohos.patch`
   - Adds a Linux non-glibc fallback for setting the stream error indicator
     without dereferencing musl's opaque `FILE` internals.
8. `0008-pthread-cancel-ohos.patch`
   - Replaces unavailable `pthread_cancel` with a short-timeout
     `sigtimedwait` loop, a shutdown flag, and an explicit `pthread_join`.
9. The Conan recipe disables NLS and the upstream `hdparm` path. HPA/DCO is
   explicitly marked incomplete by upstream and is not part of this package.
10. The recipe enables MD5, SHA-1, SHA-256, and SHA-512 as compile-time
   defaults, matching the documented dc3dd feature set.
11. The recipe builds `lib` and `src` explicitly. The release man rule invokes
    bundled Perl `help2man`, which requires `Locale::gettext`; packaging
    instead reuses the shipped `man/dc3dd.1`.

## AI review remediation

- Replaced `__OHOS__`-specific patch guards with the existing Linux
  non-glibc capability guard, so the gnulib fallbacks follow libc behavior.
- Removed the `abort()` placeholder from the opaque-`FILE` `freadseek`
  fallback.
- Replaced `pthread_cancel` with a timed `sigtimedwait` loop and an explicit
  shutdown flag plus `pthread_join`, avoiding kill-and-join races.
- Tightened temporary-directory creation from `umask 022` to `umask 027`.
- Added `pipefail` to the consumer test shell options.

## Local verification performed

- Official ZIP downloaded from SourceForge.
- SHA256 matched the SourceForge release metadata.
- SDK clang predefined macro check passed for
  `--target=aarch64-unknown-linux-ohos`.
- SDK header audit passed for `sys/mount.h`, `sys/mtio.h`, `pthread.h`, and
  the `BLKGETSIZE`/`BLKSSZGET` definitions.
- Python AST checks passed for `conanfile.py` and `test_package/conanfile.py`.
- `git diff --check` passed.
- All eight version-local patches pass local `git apply --check` against the
  extracted 7.3.1 source.
- The review-remediation revision reapplies all eight patches cleanly to a
  fresh source copy.
- The OHOS SDK clang syntax check passed for the new `sigtimedwait`,
  `errno`, and pthread shutdown logic.
- The recorded r4 device run predates this review-remediation revision; a
  new device run is still required before replacing the existing package
  reference.

## Shadow CI / device commands

The configured device is `currentUser@10.62.178.77:2222`. The Conan profile
used for the device run is `ohos-aarch64-fixed`, with the SDK toolchain and
single-job build:

```bash
export PATH=/storage/Users/currentUser/usr/local/bin:/bin:/usr/bin:/sbin:/usr/sbin:/data/service/hnp/bin
export CONFIG_SHELL=/system/bin/sh
export SHELL=/system/bin/sh
export TMPDIR="$HOME/shadow-ci/tmp-dc3dd"
export LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib
export CC=/data/service/hnp/bin/clang
export CXX=/data/service/hnp/bin/clang++
export AR=/data/service/hnp/bin/llvm-ar
export NM=/data/service/hnp/bin/llvm-nm
export RANLIB=/data/service/hnp/bin/llvm-ranlib
export STRIP=/data/service/hnp/bin/llvm-strip
conan create . -pr:h=ohos-aarch64-fixed -pr:b=ohos-aarch64-fixed \
  --build=missing --name=dc3dd --version=7.3.1 -c tools.build:jobs=1
```

The r4 Conan result was successful. It produced package revision
`fed257414d0a043dae17a27aebcadd0f`, installed `bin/dc3dd` and
`share/man/man1/dc3dd.1`, and ended with:
`PASS: dc3dd consumer smoke tests`.

The preceding device iterations are retained as troubleshooting evidence:

- r2 fixed the `fseterr.c` compile issue, then failed at link time on
  unavailable `pthread_cancel`.
- r3 linked after the pthread fallback, then failed in the release man rule
  because `Locale/gettext.pm` was unavailable.
- r4 passed after the pthread patch and the explicit `lib`/`src` build plus
  shipped-man packaging change.

For the upstream functional checks, use a writable test directory and bash:

```bash
export CONFIG_SHELL=/data/service/hnp/bin/bash
export TMPDIR="$HOME/tmp/dc3dd-tests"
mkdir -p "$TMPDIR"
cd <source-tree>/tests
"$CONFIG_SHELL" ./test-file-imaging.sh
"$CONFIG_SHELL" ./test-hashing.sh
```

On the device, `test-hashing.sh` passed 532 MD5 and 523 SHA-1 fixtures with
zero mismatches. `test-file-imaging.sh` passed 29 result stages, including
file imaging, split/join, multiple outputs, hashing, pattern generation,
validation, malformed arguments, and interruption.

The official 7.3.1 ZIP does not include
`test_data/reference_images/ref-pat.img`, so the file-imaging run used a
synthetic `ref-pat.img` generated with the built `dc3dd` binary. The test copy
also redirected hardcoded `/tmp` outputs to writable shadow-ci storage. Since
this device completed the 231 MiB fixture before the upstream `sleep 1`
interrupt race, the test copy used a 0.1-second delay for the two interrupt
cases. These test-harness adjustments were remote-only and are not repository
changes.

`test-device-imaging.sh` and `test-damaged-device-imaging.sh` require explicit
device paths and appropriate privileges. They remain deferred to the
single-device test queue.

## Handoff blockers

- Device logs contain repeated HMDFS `getcwd` diagnostic noise from the
  device-side shell, but the assertions and exit statuses passed.
- Device-node imaging tests are not run yet because they need an explicit
  block/device path, privileges, and the single-device queue.
