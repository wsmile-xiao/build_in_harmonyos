# FluidSynth 2.5.7 W0 dependency audit

Date: 2026-08-01

## Inputs

- Upstream release: `v2.5.7`, published 2026-07-25
- Downstream: DOSBox Staging 0.82.2 FluidSynth MIDI integration
- Contributor task: `id=557`, branch `feat/fluidsynth-2.5.7`
- Issue: `#1460`

## Required build graph

The selected upstream `osal=cpp11` configuration has no third-party Conan
requirements. It uses the toolchain's C++17 runtime, CMake `Threads`, and
`libm`. GCEM is a header-only source input pinned by FluidSynth itself; the
recipe retrieves the exact official revision and hash before configure rather
than treating it as a separately published runtime package.

All other discovered packages are optional features and are disabled for the
portable DOSBox consumer contract: GLib, libsndfile, ALSA, DBus, JACK,
libinstpatch, OSS, PortAudio, PulseAudio, PipeWire, readline, and SDL3.

## Integrity and collision checks

- FluidSynth archive SHA-256: PASS
- GCEM upstream-pinned SHA-256: PASS
- Device 1 system `libfluidsynth.so` scan: no match
- Device 2 system `libfluidsynth.so` scan: no match
- Unpublished Conan prerequisite references: none

## Result

`W0_RESULT=pass`. There is no R36 publication blocker for this recipe.
