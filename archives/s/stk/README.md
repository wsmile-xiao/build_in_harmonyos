# stk

The Synthesis ToolKit in C++ (STK) is a set of audio signal synthesis and processing classes.

## Features

- Oscillators, filters, envelopes, reverbs, and physical-model instruments
- File and wavetable helpers for offline audio processing
- Optional realtime audio/MIDI support through platform-specific backends

## OHOS Adaptation

- Realtime audio/MIDI backends are disabled for this package to avoid ALSA, JACK, CoreAudio, and device dependencies.
- The package builds the portable static library from `src/` only.
- Example applications are not built because they require realtime output paths when `REALTIME` is enabled.
- Portable offline synthesis/processing headers are installed under `include/stk`; realtime/network headers are not exported.

## Dependencies

- No external Conan dependencies.
- Links against the C math library.

## References

- Homepage: https://ccrma.stanford.edu/software/stk/
- Source archive: https://ccrma.stanford.edu/software/stk/release/stk-5.0.1.tar.gz
