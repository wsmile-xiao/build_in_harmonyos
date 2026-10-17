# Sound Juicer

Sound Juicer is a CD ripper for GNOME. It extracts audio from CDs to various
formats including Ogg/Vorbis, FLAC, WAV, and MP3.

## OHOS Adaptation

On HarmonyOS PC, the following GNOME libraries are not available and have been
stubbed out using the `HAVE_STUB_DEPS` preprocessor macro:

- **libbrasero** (CD burning) — stubbed
- **libmusicbrainz5** (metadata lookup) — stubbed
- **libdiscid** (Disc ID calculation) — stubbed
- **libcanberra** (sound events) — stubbed
- **totem-disc** (disc operations) — stubbed

The application compiles successfully but will not function as a CD ripper.
This serves as a platform portability exercise for HarmonyOS PC.

## Build System

- **Build system**: Meson
- **Dependencies**: glib2/2.88.0, gstreamer/1.28.3, gtk/3.24.43
- **Source**: [GNOME download](https://download.gnome.org/sources/sound-juicer/3.40/)

## Version

- 3.40.0 (built, 2026-08-27)
