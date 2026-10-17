# soloud version_1_0 adaptation notes

## Build

- Build system: none upstream (2013 first tag — demos drive SDL directly) → patch adds a headless `CMakeLists.txt`
- Conan package type: library (default static; shared also supported)
- Options: `shared=True/False`, `fPIC`
- Dependencies: none — headless build excludes the SDL back-end (`sdl/`) and all SDL demos (`demos/`, `main.cpp`)
- Patches:
  - `0001-add-headless-cmakelists.patch` — injects the headless build system (core/sinewave/speech/wav+stb_vorbis/filter; `project(soloud C CXX)` because stb_vorbis.c is C)
  - `0002-klatt-fix-gElement-declaration.patch` — upstream defect: stray `extern Element gElement[]` forward declaration followed by a `static` definition (gcc tolerated, clang rejects); the extern is dead (symbol only used inside klatt.cpp)
- Version field keeps upstream tag verbatim: `version_1_0` (platform taskBranch `feat/soloud-version_1_0`)
- conandata sources use a mirror list (official GitHub + ghfast.top + gh-proxy.com) — conan 2 native multi-source fallback for network flakiness (SDL2 2.30.10 / libosmo-netif 1.6.0 precedent)

## What gets built

Headless core engine — pure software audio mixing with zero external deps:

| Module | Files | Notes |
|---|---|---|
| core | soloud.cpp/h | mixing engine, voices, faders — no SDL references |
| sinewave | soloud_sinewave.cpp/h | basic sine AudioSource |
| speech | darray/klatt/resonator/soloud_speech/tts | Klatt TTS synthesizer, pure C++ DSP |
| wav | soloud_wav/soloud_wavstream + stb_vorbis.c | WAV loader/streamer + bundled vorbis decoder (C) |
| filter | soloud_filter.cpp/h | basic filter AudioSource |

Excluded: `sdl/soloud_sdl.cpp` (SDL back-end), `demos/` (SDL apps), `main.cpp` (SDL demo driver).

## API notes for consumers (2013 vintage)

- `Soloud::init(channels, samplerate, buffersize, flags)` + `Soloud::mix(buffer, samples)` = backend-less PCM pull; no `deinit()` exists in this version (the back-end owns shutdown)
- `Speech::setText(char*)` takes a non-const pointer
- `Sinewave::mFreq` is a public field (no setter in version_1_0)

## Validation

- OHOS aarch64 本机：`conan create` 全绿（含 test_package）
- 上游无测试套件（version_1_0 无 build system、无 tests/、demos 均为 SDL 交互式应用）→ 以 headless 消费者测试补全：无后端 init/mix、正弦输出峰值/有限性/界限校验、句柄音量/声像/流时间推进、Klatt 语音合成输出非静音、stopAll 清理
