# wildmidi 0.5.0 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device (HongMeng Kernel 1.12.0)
- Clang 15.0.4 (OHOS SDK), CMake 4.1.2
- Conan 2.29.1 (OHOS adapted)
- Profile: ohos-aarch64 (os=OHOS, arch=armv8, compiler=clang 15, Release)

## Verification

- `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`: **exit 0**
  (clean build from source; log retained at ~/wt-wildmidi-conan-create.log)
- Package `01d92cf349a0dd98ff915f4bd99a04430171517f` created
- Shared lib signed via binary-sign-tool (self-sign)
- L0a-L0e static pre-checks: passed (local re-implementation of CI gates)
- L1: upstream `ctest` executed inside build() — `1/1 tokenize Passed`
- L1e R34 semantics: test_package links the packaged `WildMidi::libwildmidi`
  target and drives real API calls (no stub)
- R38: no bin/ artifacts (WANT_PLAYER=OFF, WANT_DEVTEST=OFF) → commands.json
  not required for this library package

## Upstream tests (L1, from conan create log)

```
wildmidi/0.5.0: RUN: ctest --test-dir "…/build-ohos" --output-on-failure
Test project …/build-ohos
    Start 1: tokenize
1/1 Test #1: tokenize .........................   Passed    0.02 sec
100% tests passed, 0 tests failed out of 1
```

- test_tokenize.c: WM_LC_Tokenize_Line config-line tokenizer unit test
  (quoted paths with spaces, empty quoted strings, unterminated quotes,
  comment stripping — assert based), links libwildmidi-static.

## test_package (consumer perspective)

```
RUN: ./test_wildmidi
OK: version string = WildMidi Processing Library 0.5.0
OK: numeric version = 0x000500
OK: WildMidi_Init with built-in OPL3 bank
OK: WildMidi_OpenBuffer
OK: info: total_midi_time=500 ms, approx_total_samples=22050
OK: WildMidi_GetOutput produced 16384 bytes of PCM
ALL CHECKS PASSED
```

- test_wildmidi.c: full public API lifecycle using the built-in OPL3 FM
  synthesizer ("@opl3" config, no GUS/SF2 data files needed):
  GetString → GetVersion (0x000500) → Init → MasterVolume →
  OpenBuffer (in-memory generated MIDI) → GetInfo → GetOutput (PCM
  synthesis) → Close/Shutdown. 10 assertions.

## Test statistics

- Upstream unit tests: 1/1 passed (100%)
- test_package: 1/1 passed (100%)

## Known limitations

- Command-line player NOT built (WANT_PLAYER=OFF): OHOS has no
  ALSA/OSS/SNDIO audio stack; the player is GPL-3.0 (library stays LGPL)
- WANT_ALSA/WANT_OSS/WANT_SNDIO/WANT_OPENAL all OFF
- .so SONAME is libWildMidi.so.2 (SOVERSION 2, VERSION 2.2.0) even though
  the project version is 0.5.0 (upstream quirk, harmless)

## Result

The recipe was verified on an OpenHarmony aarch64 device and is eligible
for built status (CI upload happens after merge via release pipeline).
