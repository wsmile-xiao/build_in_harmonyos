# FluidSynth

FluidSynth is a real-time software synthesizer based on the SoundFont 2 specifications.
It is the successor to the smurf synthesizer, and is an open source project.

## Available Versions

| Version | Status | Date |
|---------|--------|------|
| 2.4.6 | built | 2026-06-01 |

## OpenHarmony Notes

- Built as static library (BUILD_SHARED_LIBS=OFF)
- No audio drivers available on OpenHarmony (ALSA, JACK, PulseAudio etc. disabled)
- No libsndfile support (SF3 disabled)
- Can be used as a SoundFont synthesis library via its C API
- Requires glib-2.0 as mandatory dependency

## Key Adaptation

The OpenHarmony musl dynamic linker doesn't honor LD_LIBRARY_PATH or RUNPATH.
The OHOS SDK's lld linker depends on libxml2.so.16 which can't be found by musl.
Solution: use GNU ld via `-fuse-ld=/data/service/hnp/bin/ld` CMake flags.
