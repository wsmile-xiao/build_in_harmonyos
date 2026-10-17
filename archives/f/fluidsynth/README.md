# FluidSynth

FluidSynth is a real-time software synthesizer based on the SoundFont 2
specification. This archive packages the `libfluidsynth` C API and the
`fluidsynth` command-line tool for HarmonyOS PC.

- Upstream: https://github.com/FluidSynth/fluidsynth
- Homepage: https://www.fluidsynth.org/
- Build system: CMake
- License: LGPL-2.1-or-later; bundled GCEM: Apache-2.0

## HarmonyOS configuration

The recipe uses FluidSynth's supported `cpp11` OS abstraction. This removes an
otherwise mandatory GLib dependency while preserving the public C API used by
DOSBox Staging. Mixer threads and native DLS support remain enabled.

Hardware and desktop service integrations are disabled: ALSA, JACK, OSS,
PulseAudio, PipeWire, PortAudio, SDL3, DBus, readline, libinstpatch, and
libsndfile. The resulting package is the portable synthesis core required by
the downstream application; it does not provide host-specific audio drivers or
SF3 decoding.

GCEM is not resolved during the build. The recipe downloads the exact official
revision and SHA-256 pinned by FluidSynth 2.5.7, then places it in the upstream
`gcem/` source directory before CMake configure. The package retains GCEM's
Apache-2.0 `LICENSE` and `NOTICE.txt` alongside FluidSynth's LGPL license.

On OHOS, the recipe supplies a build-folder-only `Platform/HarmonyOS.cmake`
that includes CMake's Linux platform rules. This removes CMake's unknown-system
fallback without changing the upstream source tree.

HarmonyOS user storage does not support CMake's versioned shared-library
symlinks. The recipe therefore emits one unversioned build artifact, restores
the upstream `libfluidsynth.so.3` SONAME, and packages the conventional shared
library names as regular-file copies.

For static packages, FluidSynth's `cpp11` backend places C++ objects behind the
public C API. The recipe therefore adds `-lm -lpthread -lc++` to the installed
`fluidsynth.pc` private libraries on OHOS. This lets an unmodified C consumer
link through `pkg-config --static` without changing its linker language.

## Validation

HarmonyOS/aarch64 W3 validation passed the same 33 logical tests in both shared
and static configurations: 30 registered upstream tests and three installed
package consumers. Both configurations were built serially. Package and
consumer ELFs were signed before execution; the shared package additionally
validated its SONAME and two regular-file aliases. The package is marked
`built`, while `commands.json` remains unpublished until the release pipeline
publishes the binary.
