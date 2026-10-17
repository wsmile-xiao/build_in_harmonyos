# yatm

yatm (Yet Another Time Machine) is a command line audio player that changes playback tempo while preserving pitch. It also supports pitch transposition in cents and semitones, and reads libsndfile formats, Speex, and MPEG audio.

## OHOS adaptation

- Builds the upstream CMake target as an application.
- Uses Conan `PkgConfigDeps` for the upstream `pkg_search_module` dependency probes.
- Uses `libao-pulse/1.2.2`, which provides the `ao` pkg-config module and ABI.
- Runtime validation uses libao's built-in `null` driver so no audio hardware or PulseAudio server is required.

## Dependencies

- `libao-pulse/1.2.2`
- `libmad/0.15.1b`
- `libsndfile/1.2.2`
- `soundtouch/2.0.0`
- `slang/2.3.3`
- `speex/1.2.1`
- `libogg/1.3.6`

## References

- https://github.com/mlang/yatm
