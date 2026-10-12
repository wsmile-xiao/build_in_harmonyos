# RHVoice

RHVoice is a free and open source speech synthesizer: applications hand it text
and receive synthesized audio through a C API callback interface.  Upstream
1.14.0 drives its build with SCons and keeps every language and voice in a
separate data repository.

## OHOS adaptation

- Builds the SCons build on HarmonyOS PC (aarch64, clang 15) with the toolchain
  taken from the Conan toolchain instead of the ambient shell environment.
- SCons itself is installed into a private prefix inside the build folder, so a
  clean CI machine can reproduce the build without a system SCons (upstream has
  no SCons package in the ohpcd registry).
- The audio backends (pulse, libao, portaudio) and the speech-dispatcher module
  are disabled: the C API delivers samples to the caller's callbacks, which is
  what a HarmonyOS application uses.
- Adaptation completeness (R40, manual confirmation pending): HarmonyOS PC has
  no system audio service, so the package is verified up to "callbacks receive
  correctly synthesized samples" (44520 samples at 24000 Hz).  Wiring those
  callbacks into the application's `AudioRenderer` is consumer-side work and is
  tracked as a follow-up on-device verification; the recipe itself contains no
  platform macros and no stub branches.
- Ships `libRHVoice`, `libRHVoice_core` and `libRHVoice_audio` plus the public
  C headers and the `RHVoice-test` synthesis tool.
- Bundles the English language pack and the Dasha-Eng voice (CC BY-SA 4.0) so
  that an engine can actually be constructed — `RHVoice_new_tts_engine()`
  refuses to start without at least one voice.  Non-free voice data is not
  bundled.

## Upstream

- Repository: https://github.com/RHVoice/RHVoice
- Adapted upstream tag: `1.14.0`
- License: LGPL-2.1-or-later (engine)
