# xpar 1.1 HarmonyOS port notes

## Source and build

- Source: upstream GitHub release `1.1`, `xpar-1.1.tar.gz`.
- Verified SHA-256: `65fd88b88a017a89e0e28566f8bf9ae169ff561a174c41a244ff9fa62364b63b`.
- Build system: GNU Autotools; the package is the `xpar` command-line executable.
- The OHOS aarch64 build enables upstream AArch64/NEON code and disables optional Linux-only io_uring.
- No Conan dependencies are required.

## Upstream test census

- Inspected the official 1.1 source archive: it contains no `tests/` directory and no Automake `TESTS`, `check_PROGRAMS`, or `check-local` registrations.
- `Makefile.am:158-259` defines one custom `.PHONY` `self-check` target. Counted as one aggregate upstream suite because its individual shell assertions are not registered or enumerated separately by upstream.
- The target covers joint and sharded encode/decode, parity recovery, integrity/authentication, malformed-input rejection, and BLAKE2b modes. `make self-check` passed: 1/1 suite (100%).

## HarmonyOS adaptation

The release ships GNU `config.guess` and `config.sub` dated 2022-01-09. On the HarmonyOS 6.0 aarch64 device, `config.guess` could not identify `uname -s = HarmonyOS`, and `config.sub` rejected `aarch64-unknown-linux-ohos`. The source changes add HarmonyOS machine detection and accept the OHOS OS/kernel tuple. They leave xpar's C implementation unchanged.

The upstream `make self-check` includes negative cases that redirect output to `/tmp/bad`; HarmonyOS mounts `/tmp` read-only. The recipe runs that test suite in a temporary copy of the build tree and redirects only those generated negative-test outputs into that temporary working directory.

Buildbot jobs 65615, 65630, and 65690 all fail at `config.status` line 608 with `./conf*/subs1.awk: Permission denied`. This is not an attempt to execute the AWK file: Autoconf first creates a private `./confXXXXXX` directory under `umask 077`, then writes `subs1.awk` into it. On the Buildbot's HMDFS user-storage filesystem, that restrictive directory mode prevents the write. The matching HMDFS failure and fix are documented by other packages in this repository (for example, `mstpd/0.2.0` and `abiword-plugin-opml/3.0.8`). The OHOS recipe now changes the generated xpar `configure` umask to 022 before configuration and fails loudly if the expected upstream pattern disappears.

Moving configure into a separate build directory did not address this failure: job 65690 already ran it from `/storage/Users/currentUser/.cache/tmp/xpar-build-...` and still failed at the same relative `./conf.../subs1.awk` write. The outer job environment listed `TMPDIR=/data/storage/el2/base/cache`, while the recipe selected `/storage/Users/currentUser/.cache/tmp`; the log does not show whether Conan hid TMPDIR from the recipe or whether the write probe rejected it. This is a separate environment discrepancy, not the cause of the `config.status` failure, because Autoconf creates this directory relative to its current working directory rather than under TMPDIR.

On the supplied HarmonyOS device, a separate early configure failure exposed an SDK-shell constraint: `/data/service/hnp/bin/bash -c pwd` fails with `getcwd` even after the parent shell changes into the temporary build directory, but succeeds when `PWD` is set to that logical path. The configure child environment now sets `PWD` to the selected build directory. This is independent of the Buildbot `subs1.awk` failure.

## Validation history

- The first Conan run exposed a typo in the recorded source checksum; the hash was corrected to the locally and device-verified SHA-256 above.
- The next run confirmed that upstream's 2022 canonicalization scripts lacked HarmonyOS support; the generated patches capture that adaptation.
- xpar 1.1 uses `.xpa` for joint parity archives; the consumer tests follow the suffix exercised by the upstream self-check.
- Buildbot jobs 65615, 65630, and 65690 reproduce the same `config.status` line-608 write failure. The 65690 log proves the out-of-source build-directory change was insufficient.
- The final HarmonyOS 6.0 aarch64 `conan create` run used the repository's `ohos-aarch64` host/build profiles and `TMPDIR=/data/storage/el2/base/cache`; it exited 0. `config.status` created `Makefile` and `config.h`, the AArch64/NEON build completed, upstream `make self-check` completed, and `test_package` passed 8/8 checks, including the HarmonyOS user-storage Unicode/space round-trip.
- A second full Conan run with `TMPDIR=/storage/Users/currentUser/tmp` put the build tree on the device's user-storage HMDFS mount; it also exited 0, generated `Makefile` and `config.h`, completed the upstream self-check, and passed all 8 consumer checks. This exercises the filesystem family implicated by the Buildbot logs. The Buildbot worker still needs to rerun the pushed branch for final worker-specific confirmation.
