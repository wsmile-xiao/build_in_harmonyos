# cutmp3

cutmp3 is a command-line editor that cuts MPEG Layer II and Layer III audio at
frame boundaries without decoding or re-encoding the audio stream.

## Features

- Displays MPEG audio stream and ID3 metadata information.
- Cuts one or more ranges without generational quality loss.
- Supports constant- and variable-bitrate MP2/MP3 input.
- Provides an interactive mode with playback through `mpg123`.

## HarmonyOS adaptation

The HarmonyOS package is built with the OHOS Clang toolchain as a static PIE.
GNU readline and ncurses are linked statically. A portability patch makes all
temporary files follow the POSIX `TMPDIR` environment variable, which points to
a writable application-owned location on HarmonyOS.

## Dependencies

- `readline/8.3`
- `ncurses/6.6`
- `mpg123/1.33.5` for interactive playback

## References

- Homepage: https://www.puchalla-online.de/cutmp3.html
- Source: https://github.com/tarjanm-movidius/cutmp3
