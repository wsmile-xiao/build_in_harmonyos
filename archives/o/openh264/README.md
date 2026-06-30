# OpenH264

OpenH264 is a codec library which supports H.264 encoding and decoding. It is suitable for use in real time applications such as WebRTC.

## Version
- Version: 2.4.1
- Release Date: 2024-01-30

## Description
OpenH264 is an open source implementation of the H.264 video codec. It provides:
- H.264 baseline profile encoder
- H.264 baseline profile decoder
- Real-time encoding and decoding support
- Suitable for WebRTC and other real-time applications

## Installation
```bash
# Install via pkg-config
pkg-config --cflags --libs openh264
```

## Usage
```c
#include <wels/codec_api.h>

// Initialize encoder
ISVCEncoder* encoder;
WelsCreateSVCEncoder(&encoder);

// Initialize decoder
ISVCDecoder* decoder;
WelsCreateDecoder(&decoder);
```

## License
BSD-2-Clause License

## URLs
- Homepage: https://github.com/cisco/openh264
- Download: https://github.com/cisco/openh264/releases

## Dependencies
- pthread
- libm (math library)

## Platform Support
- Linux
- Android
- iOS
- Darwin (macOS)
- HarmonyOS (OpenHarmony) - Added support in this build