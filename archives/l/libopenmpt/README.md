# libopenmpt

libopenmpt is a cross-platform C++ and C library to decode tracked music files (modules) into a raw PCM audio stream.

## Features

- Decodes tracked music files into raw PCM audio stream
- Supports various module formats: MOD, XM, S3M, IT, and more
- C and C++ API bindings
- Open-source and cross-platform

## Official Website

https://lib.openmpt.org/

## Versions

- 0.7.13 (2025-01-06)

## Dependencies

- zlib (optional, for compression support)

## Optional Dependencies (disabled in this build)

- libmpg123 (MP3 decoding)
- libogg, libvorbis, libvorbisfile (Ogg Vorbis support)
- libportaudio, libportaudiocpp (audio output)
- libsndfile (sample formats)
- libflac (FLAC support)
- libpulse, libpulse-simple (PulseAudio)

