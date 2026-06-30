# espeak

eSpeak is a compact open source software speech synthesizer for English and other languages. It supports many languages and can produce WAV file output or play audio through the portaudio library.

## Features
- Text-to-speech synthesis for 70+ languages
- Command-line interface (`espeak` and `speak` binaries)
- Shared library API (`libespeak.so`) for integration
- WAV file output capability
- Portaudio v19 support for audio playback

## Compiled Version
- Version: 1.48.04 (internal version string: 1.48.03)
- Platform: OpenHarmony aarch64
- Compiler: clang 15.0.4
- Dependencies: portaudio 19.7.0 (from cmd-pkgs)