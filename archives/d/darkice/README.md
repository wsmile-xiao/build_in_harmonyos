# darkice

DarkIce is a live audio streamer. It records audio from an audio input (sound card, ALSA, OSS, PulseAudio, JACK), encodes it into a format (Ogg Vorbis, Opus, FLAC, MP3 via lame, AAC via faac/fdk-aac, MP2 via twolame), and sends the stream to one or more streaming servers (IceCast, ShoutCast, or a local file).

## Version 1.6

- Build system: autotools
- Compiler: clang/clang++
- Encoding support: Ogg Vorbis, Opus, FLAC
- Audio input support: ALSA, OSS
- No lame/faac/fdk-aac/twolame (not available in build environment)
- No PulseAudio/JACK (PulseAudio shared libs incomplete, JACK not available)

## Binary

- darkice: command-line live audio streamer