# FluidSynth 2.5.7 adaptation notes

## Scope

This package provides the portable FluidSynth synthesis core needed by DOSBox
Staging. It builds the public C API, shared library, installed CMake and
pkg-config metadata, and the `fluidsynth` command-line tool.

## Source integrity

- FluidSynth v2.5.7 archive SHA-256:
  `ce27840221ab00dd59bf27e85ecbba480c6c2a7c9fbec4243658f68f59c07f4a`
- GCEM revision: `012ae73c6d0a2cb09ffe86475f5c6fba3926e200`
- GCEM archive SHA-256:
  `28159274c54e9640354852e172d10d88eb159f4e7f2fea42edbcd20105ed3526`
- GCEM license: Apache-2.0; the package preserves both `gcem/LICENSE` and
  `gcem/NOTICE.txt` under `licenses/gcem/`.

FluidSynth's `FindGCEM.cmake` downloads that revision when the git submodule is
missing. The Conan recipe obtains it in `source()` instead, so CMake configure
and build are network independent. GCEM headers participate in FluidSynth's
generated-table compilation, so its license and notice are retained in the
binary package rather than treated as download-only metadata.

## Build configuration

- Build system: CMake
- OS abstraction: upstream `cpp11`
- Mixer threads: enabled
- Native DLS loader: enabled
- Shared library: enabled by default because neither checked HarmonyOS device
  contains a system `libfluidsynth.so`
- CMake platform: build-folder-only `Platform/HarmonyOS.cmake` includes the
  built-in Linux platform rules (existing knowledge E140)
- Shared-library layout: disable CMake's versioned symlink emission on OHOS,
  restore SONAME `libfluidsynth.so.3`, and materialize the link and real names
  as regular-file copies (existing knowledge E073)
- Optional host integrations: disabled
- Conan requirements: none
- OHOS ELF signing: all 30 upstream test executables are signed before CTest;
  installed package ELFs and the two consumer executables are signed only
  after their final link/install transformation (existing knowledge E077)
- Cross builds: device-only SONAME rewriting and ELF signing are reported as
  not run; native OHOS W3/device validation keeps both operations mandatory
- Static pkg-config metadata: the installed `fluidsynth.pc` adds `-lm`,
  `-lpthread`, and `-lc++` to `Libs.private` on OHOS static builds. FluidSynth
  exposes a C API, but the `cpp11` OS abstraction contributes C++ objects, so a
  pure C consumer must receive the C++ runtime through `pkg-config --static`.
  This reusable failure pattern is recorded in draft knowledge entry E253.

The `cpp11` backend is an upstream-supported configuration and keeps the DOSBox
consumer contract independent of GLib. ALSA, DBus, JACK, libinstpatch,
libsndfile, OSS, PortAudio, PulseAudio, PipeWire, readline, and SDL3 are
optional upstream integrations and are disabled for this portable package.

## Test contract

The upstream `check` target registers 30 tests for this configuration: 28 core
unit tests, the threading test, and the SoundFont dump comparison. The Conan
consumer package builds two API consumers and runs both plus
`fluidsynth --version`.

On OHOS, the recipe first builds the shared library without versioned CMake
symlinks, restores the upstream ABI SONAME, re-signs the modified ELF, and
creates a regular-file SONAME alias before linking any consumers. It then
builds the 30 executable targets serially, signs each final ELF, and invokes
the unchanged upstream `check` target. The package step signs the installed
CLI and real shared library, then creates regular-file `.so.3` and `.so.3.5.6`
copies. The consumer recipe disables build-tree RPATH, signs both linked
consumers, and executes them via Conan's runtime environment. Missing tools,
unexpected ELF counts, or symbolic aliases are hard failures.

## W3 HarmonyOS device validation

The frozen `r8` candidate manifest is
`c2b97e238243c1232e8aad7477e076e808120b390ffed5141c44edb1448aa3dd`.
On an aarch64 HarmonyOS PC, both shared and static `conan create` runs passed
with one build job. Each configuration ran the unchanged 30-test upstream
suite and three installed-package consumers. The shared package also passed
SONAME, regular-file alias, signing, license, and no-RPATH checks. The static
package proved that a C-language pkg-config consumer links and runs with the
published private libraries.

The detailed hashes and non-inflated test accounting are in
`reports/test-report.md`.

## Failure evidence

- The first fresh shared attempt failed when HMDFS rejected CMake's
  `libfluidsynth.so.3` and `libfluidsynth.so` symbolic links. Its Conan log
  SHA-256 is
  `f3f3147545f371e69bb0fd0e1299673eaef34068fb939886b7d707cc9df2bf1c`.
- The r7 static attempt exposed the incomplete `Libs.private` contract through
  real `std::__n1::*` link failures. Its Conan log SHA-256 is
  `ca7b6b1902d98fd083bfa9a975e6338c773564a7e6d27b6d673a57107d2aa2a9`.
- After r8 shared passed, an independent package validator rechecked SONAME,
  NEEDED, AArch64, signing sections, NX, RELRO, PIE, public symbols, metadata,
  licenses, and zero symbolic links. It reported `VALIDATION_FAILURES=0`; its
  log SHA-256 is
  `902c996ed9d45e47d3cc10deb0affd9b7ec9210ac335d8db3e604767bcbc639b`.
