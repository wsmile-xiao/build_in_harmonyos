# CUPS 2.4.19 OpenHarmony PC adaptation

## Source and dependency closure

- Official source: `cups-2.4.19-source.tar.gz`
- Source SHA-256: `820984b12a67f98705785aae2dd1347fe0ac097828001d4583ff64574aed6389`
- Upstream `v2.4.19` was the latest stable release when this adaptation began.
- The OHOS/arm64 dependency graph resolved with `--build=never` for:
  - `openssl/3.5.6`
  - `zlib/1.3.1.1`
  - `libiconv/1.17`
- DNS-SD, libusb, D-Bus, PAM, GSSAPI, libpaper, ACL, and TCP wrappers are
  optional integrations and are disabled explicitly.

## Source adaptations

1. `config.guess` recognizes `HarmonyOS` and emits
   `aarch64-unknown-linux-ohos`.
2. `config.sub` accepts `ohos` and `linux-ohos` canonical forms.
3. The Autoconf inputs probe `symlink`, `pthread_cancel`, `getspnam`, and
   `endspent`; the pre-generated `configure` script carries the same probes and
   changes the two `confXXXXXX` creation masks from `077` to `022`, keeping
   `config.status` scratch writable on HMDFS.
4. `cups/thread.c` and `cups/thread-private.h` expose the cancellation wrapper
   only when `pthread_cancel` is available, without a platform macro or no-op
   stub.
5. `scheduler/auth.c` uses shadow-password APIs only when both the header and
   the platform capability are available.
6. `cups/ppd-util.c` uses `symlink` when detected and otherwise creates an
   exclusive regular-file copy. The copy handles short writes and `EINTR`,
   removes partial output on failure, and preserves the upstream interface.
7. The top-level `Makefile` invokes each official `run-stp-tests.sh` entry
   through `$(SHELL)`. This preserves the upstream script, arguments, and test
   inventory when the source filesystem does not expose its executable mode.
8. `test/run-stp-tests.sh` prefers `$TMPDIR` for its complete test root. On
   HarmonyOS it materializes the same fixture tree with checked regular-file
   copies where symbolic links are unavailable and invokes its generated
   `runcups` helper through the platform shell. It also uses the nonzero
   numeric working-directory owner in the generated scheduler configuration
   because the runtime UID has no passwd/NSS mapping; the original `$USER`
   value remains the test-report label. The generated `runcups` helper is
   launched explicitly with `/system/bin/sh` so an inherited interactive shell
   cannot add startup diagnostics to command output. Since every scheduler-suite
   client uses `CUPS_SERVER=localhost:$port`, HarmonyOS omits the redundant
   Unix-domain listener whose socket node cannot be created in the HMDFS test
   root. All upstream test inputs, runner arguments, and expected values remain
   unchanged.
9. `scheduler/cups-exec.c` can retry an explicit `/bin/sh` script or a script
   naming the configured fallback shell when direct execution returns `EACCES`.
   The fallback shell path is supplied at configure time. A dedicated argument
   vector models shebang execution explicitly: it replaces the caller-provided
   `argv[0]` with the script path while preserving every business argument from
   `argv[1]` onward. Native filters and other interpreter types retain the
   upstream execution path and error semantics.
10. The scheduler test runner and its `5.5-lp.sh` and `5.6-lpr.sh` inputs invoke
   `waitjobs.sh` through `sh`, preserving every upstream argument and wait
   interval when the source filesystem does not expose executable script mode.

## Build and packaging

- The Conan recipe builds natively for OHOS/arm64 with one make job. The
  upstream `check` target supplies its own `all unittests` prerequisites, so it
  is the single build-and-test entry instead of following a redundant `make`.
- CUPS is static on OHOS so linker and runtime resolution cannot select the
  platform's distinct `libcups.z.so` provider.
- A recipe-local `LN` helper creates checked regular-file copies where HMDFS
  cannot provide the requested symbolic links.
- On OHOS, `configure`, build, upstream tests, and install inherit the writable
  system `TMPDIR` (falling back to `/data/storage/el2/base/cache`) instead of
  placing scratch files in the Conan build directory. Unset and explicitly
  empty `TMPDIR` values both select that fallback. The configure command and
  its surrounding Conan environment use the same resolved directory.
- `PkgConfigDeps` supplies relocatable dependency metadata for configure.
- OHOS configure cache values disable the four unavailable or unusable
  interfaces, and `--with-shell-script-fallback=/system/bin/sh` supplies the
  runtime shell path without introducing source-level platform macros.
- Package install uses the platform `/bin/install` implementation on OHOS and
  passes numeric build-process UID/GID values to targets that otherwise require
  unavailable NSS names. The upstream `install-sh` remains scoped to compressed
  sample data because toybox `install` does not implement its `-z` extension.
  Install-time stripping remains disabled because post-link stripping
  invalidates OHOS code signatures.
- Public headers retain the upstream `usr/include` layout.
- `build()` executes the complete official `make -j1 check` target. The
  accompanying test manifest enumerates every unit-test target and every
  scheduler-suite input reached from that target.

## Patch reproduction

- Fifteen per-file unified patches were regenerated from a minimal
  pristine/modified dual track.
- Fresh replay binding: pristine `89bf70d2a36d2a30`, patched
  `6b6dd415b8584942`.
- A fresh extraction of the official tarball passed sequential
  `git apply --check` and application for all fifteen patches (`15/15`). The
  frozen
  modified-track hashes are:
  - `Makefile`: `1546469dba318677d8e27db401b85647db0db92eb970853551a7b91bcd198901`
  - `config.guess`: `8f18305b1455c36f08b7e9f86f0199236e21bd39d9d27554ad3cd0250b8f7411`
  - `config.sub`: `5697c92fa25fb94e4f3996e7dfd46109036f3f134d6fb9e4035b39544da146fb`
  - `configure`: `b029dcff1b789c3151f975542b24f94f2c46ab3d10e1579997c14a968cd25470`
  - `cups/ppd-util.c`: `da0bd460f32875d611901af9488fbd72fc3a576c181afc3e33d7e465a27816f8`
  - `cups/thread-private.h`: `e706b2dfaed584bf1788195e03a2354005c4b4266c091898e1d898c906baccc5`
  - `cups/thread.c`: `898b20436a31da1a3bfa8c1da9e414816762b9b1c724d4e120cf763f8290d4ce`
  - `scheduler/auth.c`: `dd2375363d2a2ca96778f7c41da4245c191b064a80318564a22ded8ec2d92221`
  - `scheduler/cups-exec.c`: `6ab463076005b25bbd4bc387bea916c9526c38346578b8c3d0e01542697b4af4`
  - `test/5.5-lp.sh`: `4a34eb0662482b606a563dcd4755f0c0e5326f775628d84fc264a72d211d2b23`
  - `test/5.6-lpr.sh`: `acbc0d05240cfcc30b99e6e4f5c0c8a5a1e937db8592e9729c366873ee4edcfe`
  - `test/run-stp-tests.sh`: `7141ed8a2b8700704cd3517f528023e49c1c2e28c74624dce1857bc373760cab`
  - `config-scripts/cups-common.m4`: `12e1ad88b10676283b7e9d3a06b860e9a5297945a0b648d2bb0ba014a7a36a6c`
  - `config-scripts/cups-threads.m4`: `0672fd4270e0352ce2633d3e3c1abc88acb2c24090ab350b9122dc1a339555f9`
  - `config.h.in`: `69fb635acbfa15bf6cc41b96e4f530c4768be3c68f9a7276ce9490b0ce795aca`

## Validation status

Complete recipe validation now passes the official `make -j1 check` target and
all 49 registered upstream entries (`49/49`) without changing test selection,
arguments, limits, or expected values. The Conan consumer reports
`CUPS_TEST_ASSERTIONS=9/9` and
`CUPS_EXEC_FALLBACK_ASSERTIONS=6/6`; the combined consumer result is `15/15`.
The unset, empty, custom, and non-OHOS TMPDIR paths pass `4/4` targeted
assertions; a fresh target build launched with `TMPDIR=""` also passes. L0,
L1, L2, L4, and L5 pass. The resulting package reference is
`cups/2.4.19#8c3d53e48f5e1e21934e8bd0f0e9dc39:48055a554d876c7a0e9b2b4f5c4ef91062e070d8#3c00cd499fcb9c6ca64680d6449d476d`.
The complete current target validation log has SHA-256
`9a19dabaf71cf0aceb711786b82b57c265a6e0e6c9c1064cff36bb8058bca8a3`.
The package contains 27 files in `bin/`, two static libraries in `lib/`, and no
`usr/bin/` directory, which matches `cpp_info.bindirs = ["bin"]`.
All 26 packaged ELF commands pass the required security checks (`26/26`): NX,
PIE, full RELRO, stack-canary, OHOS
identity, and code-sign checks. The archive status is `built`; no upload or
publication is claimed.

## Knowledge references

- E050 covers the reusable HMDFS symbolic-link failure pattern.
- E127 covers disabling unavailable pthread cancellation paths without stubs.
- E129 covers Autoconf `confXXXXXX` permissions on HMDFS.
