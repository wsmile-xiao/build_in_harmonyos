# audacious-plugins

audacious-plugins is a collection of plugins for the Audacious audio player, providing various input/output codecs, effects, and transport support.

## Available versions
- 4.5.1 (published, 2026-05-29)

## Description
audacious-plugins provides essential functionality for audacious, including:
- Input plugins: FLAC, Vorbis, MP3 (via mpg123), Game Music Emu (console), PSF, VTX, XSF, Metronom, Tone Generator
- Output plugins: ALSA, OSS4, PulseAudio, FileWriter
- Effect plugins: Background Music, Bitcrusher, Compressor, Crossfade, Crystalizer, Echo, Mixer, Silence Removal, Stereo, Voice Removal
- General plugins: MPRIS 2, Song Change
- Container plugins: ASX, ASX3, AudPL, M3U, PLS, XSPF
- Transport plugins: GIO

## Dependencies
- audacious >= 4.5 (required)
- glib-2.0 >= 2.32
- libmpg123 >= 1.12 (for MP3)
- vorbis/vorbisenc/vorbisfile >= 1.0 (for Ogg Vorbis)
- flac >= 1.2.1 (for FLAC)
- alsa >= 1.0.16 (for ALSA output)
- libpulse >= 0.9.11 (for PulseAudio output)
- libxml-2.0 (for XSPF playlists)
- zlib (for Console/GME)
