# miniaudio

**miniaudio** is a single-file (header-only) audio playback and capture library, written in C.

## What It Does

- Provides a low-level API for audio device management (playback, capture, duplex)
- Provides a high-level API (engine) with mixing, effects, and resource management
- Supports multiple audio backends: WASAPI, DirectSound, WinMM, ALSA, PulseAudio, JACK, sndio, OSS, CoreAudio, AAudio, OpenSL|ES, and null
- Includes built-in decoders for WAV, FLAC, Vorbis, and MP3
- Includes node graph system for audio effects (reverb, vocoder, channel routing, etc.)

## OHOS Adaptation

On HarmonyOS (OHOS), the following audio backends are **not available**:
- ALSA, PulseAudio, JACK, sndio, OSS (Linux backends)
- CoreAudio (macOS/iOS)
- WASAPI, DirectSound, WinMM (Windows)
- AAudio, OpenSL|ES (Android)
- Web Audio (browsers)

The **null backend** is the only available backend on OHOS. This allows:
- Library initialization (`ma_context_init`)
- Device enumeration (null device only)
- Basic API structure verification
- No actual audio playback or capture

### Build Configuration

```cmake
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DMINIAUDIO_NO_ALSA=ON \
  -DMINIAUDIO_NO_PULSEAUDIO=ON \
  -DMINIAUDIO_NO_JACK=ON \
  -DMINIAUDIO_NO_SNDIO=ON \
  -DMINIAUDIO_NO_OSS=ON \
  -DMINIAUDIO_NO_AAUDIO=ON \
  -DMINIAUDIO_NO_OPENSL=ON \
  -DMINIAUDIO_NO_COREAUDIO=ON \
  -DMINIAUDIO_NO_DSOUND=ON \
  -DMINIAUDIO_NO_WASAPI=ON \
  -DMINIAUDIO_NO_WINMM=ON \
  -DMINIAUDIO_NO_AUDIO4=ON \
  -DMINIAUDIO_NO_WEBAUDIO=ON \
  -DMINIAUDIO_NO_CUSTOM=ON \
  -DMINIAUDIO_BUILD_EXAMPLES=OFF \
  -DMINIAUDIO_BUILD_TESTS=OFF \
  -DMINIAUDIO_BUILD_TOOLS=OFF
```

### Testing

For compilation verification, use `MA_NO_LIBVORBIS` and `MA_NO_LIBOPUS` to avoid linker issues with the optional codec libraries.

## Dependencies

- **Optional**: libvorbis/vorbisfile (for Vorbis decoding) - available as static library on OHOS
- **Optional**: libopus/opusfile (for Opus decoding) - not available on OHOS

## Key Files

- `miniaudio.h` — the single header file (4.1MB, contains all source)
- `miniaudio.c` — implementation stub (`#define MINIAUDIO_IMPLEMENTATION` + `#include "miniaudio.h"`)
- `extras/` — optional node implementations and codec wrappers

## References

- Website: https://miniaud.io
- Documentation: https://miniaud.io/docs
- GitHub: https://github.com/mackron/miniaudio