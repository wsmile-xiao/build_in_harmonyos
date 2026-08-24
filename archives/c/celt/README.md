# CELT — Ultra-Low-Delay Audio Codec

CELT (Constrained Energy Lapped Transform) is an open-source audio codec
developed by the Xiph.Org Foundation (Jean-Marc Valin).  It is designed for
very low latency (5–22.5 ms) and high quality, targeting professional audio
and voice-over-IP applications.

CELT was the MDCT-based layer that, combined with Skype's SILK codec, became
the **Opus** interactive audio codec (RFC 6716).  Standalone CELT development
frozen at version 0.11.3 (2011).

## Library

- **Library name**: `libcelt0` (SONAME `libcelt0.so.0`)
- **Headers**: `celt.h`, `celt_types.h`, `celt_header.h`
- **License**: BSD-2-Clause
- **Language**: C99
- **Build system**: Autotools

## API overview

```c
#include <celt/celt.h>

CELTMode *mode = celt_mode_create(48000, 960, NULL);
CELTEncoder *enc = celt_encoder_create_custom(mode, 1, &err);
CELTDecoder *dec = celt_decoder_create_custom(mode, 1, &err);
int len = celt_encode(enc, pcm_in, 960, packet, 1275);
celt_decode(dec, packet, len, pcm_out, 960);
```

## Versions in this repository

| Version | Upstream | Status | Date |
|---------|----------|--------|------|
| 1.0.0 | 0.11.3 | built | 2026-08-22 |

## References

- <https://celt-codec.org/>
- <https://opus-codec.org/> (successor)
- RFC 6716 — Opus Interactive Audio Codec
