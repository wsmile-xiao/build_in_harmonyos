# jack 1.9.22 adaptation notes

## Scope

- Build system: bundled waf 2.0.12.
- Package scope: `libjack`, `libjackserver`, `jackd`, JACK headers, and
  `jack.pc` metadata needed by downstream clients such as qjackctl.
- Optional stacks disabled for this dependency PR: ALSA, DBus, libsamplerate,
  systemd, FireWire/FFADO, IIO, PortAudio, WinMME, CELT, Opus, Doxygen, and
  upstream tests.

## Source

- URL: `https://github.com/jackaudio/jack2/archive/refs/tags/v1.9.22.tar.gz`
- SHA256:
  `1e42b9fc4ad7db7befd414d45ab2f8a159c0b30fcd6eee452be662298766a849`

## Conan build

The recipe configures waf with a staging-friendly prefix:

```text
python3 ./waf configure --prefix=/ --libdir=/lib --pkgconfigdir=/lib/pkgconfig \
  --platform=linux --classic --autostart=none --alsa=no \
  --samplerate=no --systemd=no --tests=no
python3 ./waf build
python3 ./waf install --destdir=<package_folder>
```

`tools.build:compiler_executables` supplies `CC`, `CXX`, `AR`, and `RANLIB`
when the OHOS profile provides them.
The recipe intentionally omits `--dbus`: jack2 waf treats `--dbus` as a
value-less enable flag, so `--dbus=no` is rejected by configure. Omitting the
flag keeps DBus support off in this first-pass package while `--autostart=none`
also avoids DBus autostart integration.
For OHOS, the recipe also adds `-DJACK_DISABLE_PTHREAD_CANCEL` because the
platform may expose pthread cancellation constants without exporting the
matching cancellation functions.

## Patches

- `0001-common-JackControlAPI.cpp.patch`: calls
  `pthread_setcanceltype()` only when `PTHREAD_CANCEL_ASYNCHRONOUS` exists and
  `JACK_DISABLE_PTHREAD_CANCEL` is not defined.
- `0002-linux-alsa-hammerfall.c.patch`: keeps ALSA monitor-thread cancellation
  guarded by both non-Android and cancellation-symbol availability. ALSA is
  disabled in the recipe, but the patch keeps the source tree coherent.
- `0003-posix-JackPosixThread.h.patch`: uses a default cancellation value of
  `0` when the cancellation constant is not available.
- `0004-waflib-Context.py.patch`: replaces removed `imp.new_module()` with
  `types.ModuleType()` for Python 3.12+.
- `0005-posix-JackPosixThread.cpp.patch`: skips cancellation setup when the
  libc lacks `pthread_cancel()`, then follows JACK's Android strategy: install
  a SIGUSR1 thread-exit handler and use `pthread_kill()` plus `pthread_join()`
  for `Kill()` and `KillImp()`.
- `0006-common-JackControlAPI-signal.patch`: leaves SIGUSR1 unblocked when
  the SIGUSR1 thread-exit fallback is active. This matches JACK's Android
  control-path rationale and lets the targeted signal reach the worker thread.
- `0007-waflib-ccroot-vnum-copy.patch`: when the OHOS-only
  `JACK_WAF_VNUM_COPY=1` build environment is set, installs the unversioned
  and ABI-versioned shared-library aliases as copies of the versioned library.
  This avoids target-filesystem symlink failures without changing unrelated
  Waf symlink tasks or the Linux installation behavior.

Most pthread-related patches key off feature/symbol availability. The OHOS
recipe-defined `JACK_DISABLE_PTHREAD_CANCEL` switch covers libc variants where
the cancellation constant is present but `pthread_setcanceltype()` or
`pthread_cancel()` is not declared or exported.

## Tests

`test_package` is configured to build and run `test_jack.cpp`, a real consumer
smoke test that links through Conan's `jack::jack` CMake target and checks:

- `jack_get_version_string()`
- client and port name size APIs
- `jack_ringbuffer_create`, write/read-space, read, and free

Local validation was performed with the `JACK_DISABLE_PTHREAD_CANCEL` fallback
enabled:

- A waf configure with `--tests=yes` followed by `python3 ./waf build`
  completed all 138 scheduled build tasks.
- The upstream executable-test denominator is all four executable-level tests.
  Only a completed zero-exit execution is counted in its numerator:

  | Executable | Result | Counting rationale |
  | --- | --- | --- |
  | `tests/jack_cpu --time 1 --cpu 1` | passed | Completed against a dummy JACK server. |
  | `tests/jack_test --time 1 --quiet` | failed, exit 139 | The same invocation also exits 139 in an ordinary unguarded Linux build. This establishes a reproduced upstream/baseline failure, not a HarmonyOS-specific pass; its precise root cause remains unassigned. |
  | `tests/jack_iodelay` | not passed | It requires a physical audio input/output loopback. Without that hardware path it reaches the test's deliberate five-second timeout, and a timeout is not a pass. |
  | `tests/jack_multiple_metro` | not run, not passed | It requires interactive control of JACK server/metronome state; no unattended deterministic server-control harness was available. |

  The executable-level upstream result is therefore **1/4 (25.0%)**:
  `jack_cpu` is the sole numerator; the exit-139 baseline failure,
  timeout-limited loopback test, and unrun interactive test each remain zero.
  Full upstream coverage is incomplete and must not be represented as a passing
  rate. The 138/138 Waf figure is a build-task count, not an upstream test
  result. The consumer smoke was also compiled and run directly against the
  guarded headers and `libjack` (1/1 passed), but that is a separate consumer
  result and cannot replace the four-executable upstream rate. Reaching 100%
  requires physical loopback hardware, an automatable server-control harness,
  and a fix for or upstream confirmation of the reproduced `jack_test`
  baseline crash. A local `conan create` preflight was attempted, but source
 retrieval from GitHub timed out before Conan reached its build or test-package
 phases; it is not counted as a successful Conan validation.
