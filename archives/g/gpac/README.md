# GPAC — Multimedia Framework

GPAC is an open-source multimedia framework for research and academic purposes,
focused on filtering and stream processing. It provides MP4Box (ISO base media
file format tools) and the gpac filter engine.

## Key Tools
- **MP4Box**: ISO media file format manipulation (import, export, split, hint, dash)
- **gpac**: Command-line filter engine for multimedia processing

## HarmonyOS Build Notes (v2.4.0)

### Build Configuration
- Custom configure script (not autoconf-generated), requires `--target-os=Linux` on HarmonyOS
- `--static-bin` builds static libgpac + MP4Box binary
- `--disable-resample` required when compositor is disabled (resample_audio depends on audio_mixer)

### Known Limitations
- MINI build (no encoders, decoders, audio/video output)
- SSL/crypto disabled (could be enabled with OpenSSL available)
- G0 clean-verify fails because configure can't auto-detect HarmonyOS platform
- `cp --no-preserve` not supported by toybox cp on HarmonyOS (affects `make install`)

### Dependencies
- zlib (system-provided)
