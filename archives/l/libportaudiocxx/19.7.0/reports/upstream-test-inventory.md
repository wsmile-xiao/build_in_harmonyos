# Upstream test inventory

libportaudiocxx 19.7.0 is the `bindings/cpp` subtree (PortAudioCpp, library
version 12) of the official PortAudio 19.7.0 source archive. The subtree does
not ship a dedicated test suite:

- `make check` has no test targets: `SUBDIRS` is `lib include` and the
  library builds with no `TESTS` declarations.
- The subtree's only runnable programs are the `example/devs.cxx` and
  `example/sine.cxx` demos, which are declared `noinst_PROGRAMS` (built only
  in the `bin` subtree, not installed) and require a working audio device.
- PortAudioCpp's validation is exercised through its consumers (e.g. the
  PortAudioCpp project's own examples and downstream packages).

## Upstream tests in the device gate

No upstream test program is packaged. Coverage of the binding layer is
provided by the explicit consumer test in `test_package/`
(`test_portaudiocxx.cxx`), which exercises the public C++ API without audio
hardware:

1. `portaudio::System::version() == 1246976` (PortAudio 19.7.0 version query)
2. `portaudio::System::versionText()` non-empty
3. `portaudio::System::initialize()` succeeds
4. `hostApiCount() >= 0` and `deviceCount() >= 0` (enumeration consistency)
5. host API iterator traversal matches `hostApiCount()`
6. `sizeOfSample(paFloat32) == 4`
7. out-of-range `deviceByIndex()` throws `portaudio::PaException`
8. `portaudio::System::terminate()` succeeds
9. (OHOS only, under `#if defined(__OHOS__)`) `hostApiCount() == 0`,
   `deviceCount() == 0`, and `nullDevice().index() == -1` — the no-backend
   platform behavior of the OHOS portaudio package

## Deferred tests

The `devs` / `sine` example programs require an audio device and are not
meaningful in the single-package gate; the OHOS package intentionally has no
ALSA / JACK / OSS backend, and the device test environment provides no
controlled audio fixture. They are not modified or weakened — they are simply
not part of the packaged artifact (the `bin` subtree is excluded from
`SUBDIRS`, see `0001-bindings-cpp-Makefile.in.patch`).

## Consumer coverage

The explicit test package provides deterministic no-hardware coverage of the
exported C++ API and package metadata. The consumer remains subject to shadow
CI's destructive R34 dependency test.
