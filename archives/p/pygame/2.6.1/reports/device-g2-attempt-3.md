# HarmonyOS PC G2 attempt 3

- Run ID: `20260904T181656Z-10027`
- Result archive: `output/pygame-2.6.1/999pygame-device-results.tar.gz`
- Result archive SHA-256: `c07a07d70ac0edccfdc21888b8d0a9e4b90ad534479ebf6f717af5037ed44d1`
- Preceding gates: language preflight PASS; W0 10/10 direct references PASS;
  private SDL2 runtime ELF validation PASS; wheel build/sign/repack/reinstall PASS
- G2 exit code: 1

The installed signed wheel executed the complete upstream runner. Its final
marker reported 1,855 cases: 1,746 ordinary passes, 14 expected failures, 47
skips, 12 failures, and 36 errors. The 48 unexpected results have five bounded
causes:

1. The device image has no `fc-list`, leaving pygame's system-font registry
   empty and affecting `font_test`, `ftfont_test`, and `sysfont_test`.
2. PortMidi was deliberately omitted because its dependency is absent from the
   published graph; the eight noninteractive `midi_test` cases imported it.
3. `libSDL2_mixer.a` contains WAV/minimp3 registration objects, but normal
   archive extraction omitted them when the extension linked, so all 23 music
   loading cases reported `Unrecognized audio format`.
4. The published SDL_mixer package deliberately disables Vorbis/OGG, so its OGG
   cases require an explicit capability skip after the registration fix.
5. `mixer_test.ChannelTypeTest.test_queue` used the disk audio backend and its
   file-writing timing exceeded the upstream assertion window.

The recipe now derives and validates a private whole-archive
`libpygame_sdl2_mixer.so`, runs tests with SDL dummy audio, and uses real
runtime probes. Missing system-font/PortMidi and pure OGG cases are explicit
skips; mixed OGG/WAV cases retain their WAV branches, and unavailable SDL_ttf
script shaping validates its error path. The package source and upstream test
files remain unchanged.

The follow-up device run reached all upstream cases and reduced the prior
failure set to one case: `mixer_test.ChannelTypeTest.test_queue`, where dummy
audio completion timing left a channel busy at the upstream assertion. The
state-based wait correction is recorded in `device-g2-attempt-4.md`.
