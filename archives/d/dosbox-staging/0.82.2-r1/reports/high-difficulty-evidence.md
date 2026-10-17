# DOSBox Staging 0.82.2-r1 high-difficulty evidence

## 1. Claim boundary

This report records the item-by-item evidence for path C. Fresh dependency W0
passes with 17 graph nodes, `info_invalid=0`, `Missing=0`, and 15 downloaded
OHOS packages under `--build=never`. The current r178 target transaction used
one launch on `10.62.150.125:2222`, passed all 24 upstream Meson entries (23
`OK`, one `EXPECTEDFAIL`) and the installed production capability flow 4/4,
passed the frozen validator, and released with task roots and PID absent on
independent readback. The earlier r71 and r172 transactions remain immutable
diagnostic/history evidence only.

The historical unit-test and `--version` evidence alone did not establish that
SDL could create a visible native surface, that a non-dummy audio backend
emitted samples, or that a guest workload executed under dynrec. The r178
transaction now supplies the required production-boundary observations for all
three capabilities; no path C claim treats `--version` as a substitute.

The candidate uses the official `v0.82.2` source archive:

- URL: `https://github.com/dosbox-staging/dosbox-staging/archive/refs/tags/v0.82.2.tar.gz`
- SHA-256: `387c97b373c3164ab5abbbc2b210bf94b5567057abe44ee1e8b4d4e725bd422c`
- tag commit: `f8c24f87d7fb0f41c2b7ef2a1aa97d16a52206be`

## 2. Source scale and architecture-specific implementation

The locked official source tree contains 1,387 tracked source-distribution
nodes. A suffix audit reports 274 C++ implementation files, 62 C implementation
files, 314 headers, two assembly files, 41 `meson.build` files, and one
`meson_options.txt`. These numbers describe source scale; they are not test
counts.

The emulator is not a thin command-line wrapper. Representative high-cost
areas include:

| Area | Representative source | Concrete difficulty |
| --- | --- | --- |
| CPU execution | `src/cpu/core_dynrec.cpp`, `src/cpu/core_dynrec/` | 18 architecture-specific dynamic-recompiler files, including `risc_armv8le.h`; generated host instructions, register allocation, page protection, and cache invalidation must remain valid on AArch64. |
| CPU alternatives | `src/cpu/core_dyn_x86/`, `src/cpu/core_normal/`, `src/cpu/core_prefetch/` | Build and runtime selection must not accidentally select an incompatible host backend. The wider `src/cpu/core_dyn*` family contains 28 files. |
| Rendering | `src/gui/render.cpp`, `src/gui/sdlmain.cpp`, `meson.build:1000-1005` | Upstream's `use_opengl` option requires a desktop `gl` dependency, while the selected OHOS route retains SDL texture rendering. |
| Networking | `src/hardware/ipx.cpp`, `src/hardware/modem.cpp`, `src/hardware/ne2000.cpp` | SDL2_net and libslirp are both retained; their feature macros are generated at `meson.build:436-439`. |
| MIDI and synthesis | `src/midi/`, `src/hardware/mame/`, `meson.build:1007-1042` | FluidSynth and mt32emu remain enabled, bringing their own GLib and synthesis/runtime contracts. |
| Platform selection | platform guards throughout `src/` | A static scan records 231 `_WIN32`, Linux, Apple, BSD, Haiku, or related platform-guard references. OHOS must take an intentional supported branch instead of inheriting a Linux-only assumption. |

The dynamic core emits host instructions at runtime. This makes executable
memory behavior, page size, AArch64 code generation, and final ELF signing part
of the validation surface. The recipe fixes `pagesize=4096`, builds position-
independent executables, and requires a single `.codesign` section on every
generated test ELF and on the packaged `dosbox` binary. Those choices remain
subject to target W3 evidence.

## 3. Build-system and release-archive difficulty

Upstream uses Meson with C and C++20 and spreads target definitions across 41
`meson.build` files. Configuration performs compiler-link probes, atomics and
thread checks, provider selection, generated configuration, source-subproject
resolution, and a shell version query.

The official release archive intentionally has no `.git` directory, but
`meson.build:4-7` executes `scripts/get-version.sh`, whose upstream form asks
Git for both the source root and short commit. The adaptation patch:

1. preserves the original behavior when real Git metadata exists;
2. derives the source root from the script location for an official archive;
3. requires `DOSBOX_SOURCE_GIT_HASH` instead of inventing an archive hash;
4. binds that value to `f8c24`, the short form of the official tag commit;
5. fails configuration when neither source of provenance is available.

The patch is deliberately limited to this release-archive portability gap. It
does not replace version parsing, change the reported upstream version, or
modify emulator behavior.

## 4. Direct and transitive dependency topology

The selected product configuration has eleven explicit Conan requirements:

| Direct Conan reference | Upstream role | Selected boundary |
| --- | --- | --- |
| `iir1/1.10.0` | mixer filtering | shared provider |
| `opusfile/0.12` | Opus stream decoding | shared provider; transitively uses libogg, Opus, and OpenSSL in the selected recipe |
| `libogg/1.3.5` | Ogg container provider required by opusfile | direct provider; emits canonical `ogg.pc` for the consumer closure |
| `sdl2/2.32.10` | window, input, audio, timer, and renderer substrate | published static/default provider with NativeWindow, OpenGLES2, and OHAudio support |
| `zlib/1.3.2` | compressed data | direct provider selected instead of zlib-ng; matches libpng's exact edge |
| `libpng/1.6.58.2` | PNG image handling | shared provider; exact candidate selects zlib 1.3.2 and removes the 1.6.58.1 dangling-link defect |
| `speexdsp/1.2.1` | resampling and DSP | published static/default provider |
| `sdl2_net/2.2.0.1` | modem and IPX networking | published static/default provider; depends on the exact SDL2 2.32.10 candidate |
| `libslirp/4.9.3` | user-mode Ethernet networking | shared provider; depends on GLib |
| `fluidsynth/2.5.7` | SoundFont MIDI synthesis | shared leaf provider with no Conan transitive edge in the selected recipe |
| `mt32emu/2.7.1` | MT-32 synthesis | shared provider with its selected internal resampler |

The old forced `libpng/1.6.58` graph is obsolete and is not used as current W0
evidence. Fresh isolated `--build=never` resolution of exact
`libpng/1.6.58.2` produced 17 nodes with `info_invalid=0` and `Missing=0`, then
downloaded and materialized 15 non-skipped packages and manifests with
zero non-skipped RREV/PID/PREV delta from the recipe graph. The 16-reference
closure's layer-zero leaves are IIR1, SDL2, zlib, SpeexDSP, mt32emu, libogg,
Opus, OpenSSL, PCRE2, libffi, and FluidSynth.
Layer one adds libpng -> zlib, SDL2_net -> SDL2, opusfile ->
libogg/Opus/OpenSSL, and GLib -> PCRE2/libffi. Layer two adds only libslirp ->
GLib. The selected OpenSSL recipe does not declare zlib, the selected GLib
recipe declares neither gettext nor zlib, FluidSynth 2.5.7 has no Conan edge,
and mt32emu uses its internal resampler; older speculative edges are not part
of this candidate.

The W3 runner requires an aggregate cache manifest for all 16 references. The
final manifest binds recipe revision,
package ID, package revision, package folder, `conanmanifest.txt`, every
regular member, and every symbolic link. Conan will disable remotes and allow
only `--build=dosbox-staging/*`; an absent or altered dependency is a hard
failure instead of an implicit rebuild.

Upstream also ships 16 source components under `src/libs`. They are part of the
main source archive and must not be misreported as separate external packages:

| Component | Files | Component | Files |
| --- | ---: | --- | ---: |
| decoders | 21 | enet | 3 |
| ESFMu | 7 | ghc | 9 |
| loguru | 5 | manymouse | 10 |
| mverb | 3 | nuked | 4 |
| PDCurses | 59 | residfp | 49 |
| simde | 2 | stb_truetype | 1 |
| tal-chorus | 10 | whereami | 7 |
| YM7128B_emu | 6 | zmbv | 16 |

## 5. Feature decisions and platform boundary

Four optional providers remain enabled: SDL2_net, libslirp, FluidSynth, and
mt32emu. Disabling them merely to make dependency resolution easier would
change the submitted product surface.

Five options are explicitly disabled:

- desktop OpenGL: current OHOS EGL/GLES material does not prove Meson's
  `dependency('gl')` desktop contract; SDL texture and non-blocking texture
  rendering remain available;
- ALSA: upstream treats it as an auto-on Linux MIDI backend and no OHOS product
  requirement has established this backend;
- XInput2: importing the full X11 input stack is outside the selected product
  surface;
- zlib-ng: the validated zlib provider is selected and native-SIMD fallback
  ambiguity is removed;
- Tracy: profiling instrumentation is not part of the release package.

These are explicit scope decisions, not claims that the corresponding upstream
features passed on OHOS.

## 6. Test framework and exact entry accounting

`tests/meson.build` registers exactly 24 independent Meson entries: three
explicit targets and 21 table-driven targets. The source tree has 24 matching
`*_tests.cpp` files. GoogleTest assertions, individual parameter values,
sources, and repeated build configurations are not counted as extra tests.

`gtest example` is declared with `should_fail: true`; it counts as passed only
when Meson records the expected program failure as terminal `EXPECTEDFAIL`.
The recipe enables unit tests only in an executable environment and validates
the JSON log one-to-one. Completion order is irrelevant, but every name must
be unique and must be either the exact upstream name or the exact
`dosbox-staging:` project-prefixed name. The other 23 entries require `OK`;
missing, duplicate, unknown, skipped, timed-out, failed, interrupted, or any
terminal different from the entry's expected result stops packaging.

The framework is provided from fixed official inputs:

- GoogleTest 1.14.0 source SHA-256:
  `8ad598c73ad796e0d8280b082cebd82a630d73e73cd3c70057938a6501bba5d7`
- Meson WrapDB patch SHA-256:
  `2e693c7d3f9370a7aa6dac802bada0874d3198ad4cfdf75647b818f691182b50`
- Meson `wrap_mode=nodownload` after both files are placed in
  `subprojects/packagecache`.

The installed package adds one logical consumer flow with four capability
checks. Version identity remains a prerequisite, but is not treated as native
capability evidence. The flow then starts the same packaged executable through
three independent production configurations:

1. `SDL_VIDEODRIVER=nativewindow` and `SDL_RENDER_DRIVER=opengles2` are bound
   to a decimal surface identifier and positive dimensions. The application
   must initialize SDL, create its window and renderer, and emit a marker only
   after `SDL_RenderPresent` (or the OpenGL swap path) returns. A dummy,
   offscreen, software-only, or missing renderer marker is rejected.
2. `SDL_AUDIODRIVER=ohaudio` opens the provider's F32 playback stream. A
   test-only 440 Hz signal is mixed into DOSBox's master `output_buffer` before
   capture and final normalization. The SDL callback only reads the received
   bytes and emits a marker when finite, non-zero samples are observed with
   the actual `ohaudio` driver name. It never fills a silent callback buffer.
3. The CPU configuration selects `core=dynamic`, the production dynamic-core
   run function emits an entry marker, and an autoexec guest command prints
   `DOSBOX_DYNREC_GUEST_SENTINEL`. Both the host-core marker and the guest
   output are required; either one alone is insufficient.

The logical terminal is `DOSBOX_CONSUMER_FLOW|4/4|PASS`. The four checks are
counted once each even though the version check and the two dynrec assertions
are implemented inside one shell flow. Any missing marker, unexpected backend,
non-zero exit, or malformed NativeWindow tuple fails closed.

### Native GUI execution analysis

The GUI requirement concerns the complete path from the packaged executable to
the OpenHarmony compositor boundary. SDL's video-driver name is read only after
initialization and is checked against the explicitly requested `nativewindow`
driver. Before initialization, the consumer supplies a decimal surface ID and
positive width and height through the task-owned runtime environment. The
production entry point validates all three values and refuses to continue when
one is absent, non-numeric, or empty; this prevents an environment typo from
silently falling back to SDL's dummy or offscreen providers. Once initialized,
DOSBox creates its normal window and texture renderer. The probe is attached to
the existing presentation functions rather than to a standalone SDL fixture:
the texture path emits its marker after `SDL_RenderPresent`, and the optional
OpenGL path emits its marker after `SDL_GL_SwapWindow`. The marker also records
the renderer reported by `SDL_GetRendererInfo`, which permits the validator to
reject a window that exists but is not backed by the OpenGLES2 renderer exposed
by the selected SDL2 package.

This design addresses a common false positive in cross-platform adaptations.
`SDL_CreateWindow` alone proves allocation of a window object, while a driver
name alone proves only selection. Neither demonstrates that a render target was
created or that a frame reached the compositor. Conversely, a screenshot API
or an external component snapshot is not part of SDL's rendering contract and
may have different ownership rules on API20. The application-level marker is
therefore emitted at the final present operation and is accepted only when the
same invocation reports the requested driver and OpenGLES2 renderer. The test
does not claim colorimetric display accuracy, input latency, compositor
capture, or physical panel characteristics; those are distinct product
requirements and remain outside this adaptation's denominator.

### OHAudio and mixer-path execution analysis

The audio requirement concerns application-produced PCM reaching a real
OpenHarmony audio callback. The DOSBox mixer stores stereo samples as
`AudioFrame` values in the master queue and asks SDL for an `AUDIO_F32SYS`
stream. The capability signal is inserted only when both
`DOSBOX_CAPABILITY_PROBE=1` and `DOSBOX_CAPABILITY_AUDIO_TONE=1` are present.
It is added to the master mix after the normal channel, reverb, chorus, gain,
and compressor stages, but before capture and the final float normalization.
Consequently it traverses the ordinary queue, format conversion, SDL device
open, and callback scheduling. Normal user executions never enable the signal.

The callback is intentionally observational. It clears the requested buffer
according to the existing production contract, dequeues the mixed frames, and
then reads complete float samples with byte-preserving copies. It records a
marker only after a finite sample whose magnitude exceeds the silence
threshold is present, and includes the runtime driver name and byte count. The
consumer requires `driver=ohaudio`, a positive byte count, and `nonzero=1`.
Writing a synthetic waveform in the callback would be invalid because it could
make a callback appear active while the mixer was silent or bypassed. The
master-boundary signal avoids that ambiguity while remaining bounded and
test-only. This proves application-to-provider PCM delivery and callback
progress, not speaker acoustics, route selection, latency, volume policy, or
the musical content of an arbitrary DOS game.

### Dynamic-recompiler guest execution analysis

The dynamic-recompiler requirement is stronger than observing process startup
or printing a static capability label. DOSBox's `core=dynamic` setting selects
the architecture-specific dynamic core; the core translates guest instruction
blocks into host code, maintains executable cache pages, and returns through
the production run loop. The source patch places a one-time marker at the
entry of both the generic dynrec and dynamic-x86 run functions, guarded by
`DOSBOX_CAPABILITY_DYNREC=1`. The marker is evidence that the selected
production function was entered, not that a test helper was linked.

The consumer additionally creates a task-local configuration with
`[cpu] core=dynamic` and an autoexec sequence that prints
`DOSBOX_DYNREC_GUEST_SENTINEL` from inside the emulated DOS command
environment. The validator requires both the host entry marker and the guest
sentinel in the same process output. This pairing rules out a static marker,
an early configuration exit, or a normal-core fallback being reported as
dynamic execution. On AArch64 the complete target transaction remains
necessary to validate generated host instructions, executable-memory
permissions, cache invalidation, page-size assumptions, and ELF signing. A
host fixture or `--version` invocation cannot establish those properties.

The detailed framework and runner design is in
`reports/test-framework-toolchain-wiki.md`; the earlier r172 values remain
historical context, while the current result is bound to the r178 values and
hashes below.

## 7. Fresh W3 evidence design and validation cost

The target run is intentionally one-shot and fail closed:

1. verify a clean committed candidate HEAD and full candidate manifest;
2. require a separately created target-release record;
3. verify all ten dependency evidence manifests, states, summaries, and unique
   PASS terminals before creating a result directory;
4. verify the 16-reference aggregate cache manifest against every archive
   member, then extract the cache into a fresh Conan home;
5. seed only the three source/framework files bound by official URL, bundle
   path, and SHA-256;
6. invoke one Conan create with remotes disabled and only the main package
   selected for build;
7. discover and execute all 24 upstream entries, signing target test ELFs;
8. execute the single installed-package flow;
9. prove pre-existing dependency package files and links did not change;
10. inspect the final AArch64 ELF, unique `.codesign`, dynamic dependencies,
    and absence of embedded runtime paths;
11. publish a relative-path SHA-256 evidence manifest and a unique PASS state;
12. download the persistent evidence, replay its terminal chain, and perform
    owner-safe release with two clean scans.

The external Conan command has an eight-hour ceiling. This ceiling is a safety
limit, not a claimed duration. Any timeout yields no passing evidence. The
final cost includes ten dependency closures, the main C++20 build, 24 test
executables, target signing, one package consumer, dependency integrity
readback, artifact inspection, evidence transfer, and terminal validation.

## 8. Contest evidence items

### Test framework/toolchain

The repository includes the exact test inventory, hash-pinned framework
inputs, runner contract, negative validator mutations, and Wiki-ready detailed
text. The associated points must not be requested until the Wiki page is
published and the page links to final 24/24 evidence.

### Service setup

Not applicable. DOSBox Staging is an interactive emulator application, not a
Tor, Apache, Tomcat, or similar hosted service. No service-setup points are
requested.

### Official resource retrieval and dependency closure

Three official downloads are URL- and SHA-256-pinned, and the ten-item direct
dependency contract plus selected transitive closure are documented. The r172
W3 proves the closed cache and the full 24-entry target suite; publication and
release remain separate post-merge operations.

## 9. Evidence table after execution

| Evidence | Required value now | Current state |
| --- | --- | --- |
| dependency W0 | fresh exact graph, `info_invalid=0`, `Missing=0`, `--build=never` | `PASS: 17 nodes; 15 packages downloaded and installed` |
| committed candidate HEAD | one 40-character SHA | `3901f085f182354cc7033f34cec8acb8507d192e` |
| candidate manifest | SHA-256 and exact file count | `2200e38fd4c78aa2932226a2a8a3b6c35fcebacc82f4c3b4973338bc268df57c`, 73 bundle files |
| dependency cache | SHA-256, no implicit dependency rebuild | `9f1036f50321c22bba844339cf0f7e878d86c081efe5745e24bd0267b4c201ed`, PASS |
| official source/framework | three fixed SHA-256 checks | `PASS` |
| upstream Meson entries | 23 unique `OK` + 1 unique `EXPECTEDFAIL` | `24/24 PASS` |
| installed capability flow | 4/4 | `4/4 PASS` |
| packaged ELF | AArch64, one `.codesign`, no RPATH/RUNPATH | r178 validator accepted the target artifact |
| final evidence readback | replayable SHA-256 closure | r178 evidence manifest `8ad58251ae8419a3e912889520d3e2dab0c2e2c64066cbc070ff472cb50e4371`, validator PASS |
| platform capability extension | graphics, non-dummy audio, dynrec guest workload | `PASS_R178` |

The PR description retains the platform's existing six-section structure. This
report binds the current r178 capability result while preserving r71/r172 as
immutable diagnostic history; no result from one transaction rewrites another
transaction's receipt chain.

## 10. Current-head HD1-HD4 reassessment

The classification was reassessed after the current-head r178 target result.
Each item below records a direct match decision and the evidence that supports
it; the result is not inferred from patch count, elapsed time, or source size.

| Criterion | matched | Current evidence | Causal conclusion |
| --- | --- | --- | --- |
| `HD1_PRIVATE_OS_INTERFACES` | `true` | `harmony-test-r178.log` SHA-256 `15ba178ea4dc89c1f488dcbb9672120c59cf37351248c957c4d24329c02b9172`; target consumer markers for NativeWindow/OpenGLES2 and OHAudio | The claimed capabilities cross NativeWindow and OHAudio provider boundaries that are not represented by a portable SDL-only abstraction. |
| `HD2_PRIVATE_TOOLCHAIN` | `true` | r178 `summary.log` SHA-256 `287c8fbb9a0e51c4f740c5d9e6bbe97641002b832093679b375b67e5e11d2155`; target binary `0270effeadcf6c4e3469e7b5b01fd4a5e03fd96f06ed773b997a6c1927de8e30`; signed AArch64 artifact accepted by the frozen validator | The build requires the task-owned OHOS clang/sysroot/native-image/signer closure; a generic Linux recipe cannot reproduce the target artifact contract. |
| `HD3_COMPLEX_ARCHITECTURE` | `true` | `artifacts/dosbox.dynamic.log` SHA-256 `cb9c23cdb11ba6aefb3175c498a0bec9108326c2cb70ee72fe727dcbe029171b`; consumer `guest_execution=1` and guest sentinel; one-launch receipt chain | Dynamic host-code generation, executable-memory permissions, cache invalidation, and guest progress form a coupled AArch64 runtime boundary. |
| `HD4_LARGE_DEPENDENCY_TEST_COST` | `true` | `input/inventory.tsv` SHA-256 `6443169942de586ab6371670b83691df42ed2934c6aead7609a6fba7695225ac`; dependency cache SHA-256 `9f1036f50321c22bba844339cf0f7e878d86c081efe5745e24bd0267b4c201ed`; upstream `24/24` and consumer `4/4` | The exact 17-node graph, 15 non-skipped package cache, 24 target entries, and separate four-assertion consumer flow require independent denominator and closure validation. |

All four criteria therefore remain `matched=true`; the task keeps
`adaptation_paths: A+B+C` and the `【高难度挑战】` prefix. The current r178
result is the only current-head capability verdict. r71/r172 results remain
immutable historical records and are not combined with r178 counts or receipt
chains.
