# DOSBox Staging 0.82.2-r1 adaptation notes

## Current boundary

Dependency publication W0 passes for exact `libpng/1.6.58.2` and
`zlib/1.3.2`. A fresh isolated OHOS/armv8 graph resolved 17 nodes (the root
plus 16 Conan references) with `info_invalid=0` and `Missing=0`. The same fresh
home downloaded all 15 non-skipped packages with `--build=never`; install
materialized 15/15 package folders and manifests with zero RREV/PID/PREV delta
from the recipe graph. No old binary or local fallback build was accepted.
The recipe validates OHOS compiler and archiver names as target POSIX paths
during generation and defers target filesystem checks to `build()`. The
production install passed on Windows, while relative compiler and archiver
profiles both failed closed. The consumed r16 target transaction reached the
real C++ build and failed before tests because Conan's generated `opusfile.pc`
exposed only `include`, while the published header is
`include/opus/opusfile.h`. Its terminal remains immutable `ERROR`. The narrow
consumer-side repair rewrites only the generated opusfile provider contract
after `PkgConfigDeps`: `include/opus`, `-lopusfile`, and the original
`Requires: opus`.

The current authoritative historical r71 transaction used one launch on
`10.62.148.108:2222` for HEAD
`4966be612920a2a4cb8d39b4970aa3d7b4639eb1` and staged tree
`fc51ceb58f9676c456864422637445310c49451e`. It passed the full upstream suite
24/24 (23 `OK`, one `EXPECTEDFAIL`) and the installed-package flow 1/1. Its
package RREV/package-ID/PREV are
`01b0062fe9f7abff039ff9330af7369c` /
`b2dfee4cb2c2d1983f430889a3e9b20656ef587f` /
`d3bc0865a95ec0c4eb99866fa2aea84b`. The frozen remote validator passed, the
52,199,424-byte evidence tar has SHA-256
`8ce587ab96b1bc41bf8badde5abf430a6f9cd320da8cfba17265e38c9c02088f`,
and release plus two final clean scans passed.

This historical W3 proves the complete 24-entry upstream unit-test inventory
and the installed `--version` flow. It does not prove interactive SDL graphics,
non-dummy audio output, or a guest workload under the dynamic recompiler. The
new capability successor adds a source patch and one installed consumer flow
with four checks. It must report real backend availability, mixer output, and
guest execution instead of treating `--version` as a substitute.

The capability patch is bound to the same v0.82.2 source archive and changes
only probe-gated production paths. The NativeWindow probe validates the decimal
surface tuple before SDL initialization and emits a marker after an actual
`SDL_RenderPresent` or OpenGL swap. The OHAudio probe adds a deterministic
signal at DOSBox's master mixer boundary before final normalization and lets
the SDL callback inspect, but never modify, received float samples. The dynrec
probe selects `core=dynamic`, records entry into the production dynamic core,
and requires a guest autoexec command to print a sentinel. A marker fixture
passed all four checks and an audio-marker omission failed closed; target
execution remains pending until a fresh signed W3.

## Dependency and feature decisions

- Keep IIR1, opusfile, SDL2, zlib, libpng, and SpeexDSP as mandatory providers.
- Keep SDL2_net, libslirp, FluidSynth, and mt32emu enabled.
- Disable desktop OpenGL explicitly. The existing OHOS EGL/GLES material does
  not by itself satisfy the upstream Meson `dependency('gl')` contract.
- Disable ALSA because upstream only auto-enables it for a Linux Meson host and
  the OHOS build has no established ALSA product requirement.
- Disable XInput2 to avoid accidentally importing an unvalidated X11 stack.
- Use published zlib 1.3.2 rather than zlib-ng, and bind exact
  `libpng/1.6.58.2`, whose published recipe selects the same zlib version.
The fresh W0 binds libpng RREV `406755c87887b1f13e21054ce2a0359f`, PID
`85c8cc54d75c9c9c5783992861c4dbe10ae5767d`, and PREV
`64e0e27d66a1f01a7c54eea0a5355e02`.

The current capability transaction r178 completed one exact-byte target
transaction on `10.62.150.125:2222` after correcting the transfer archive's
top-level `bundle/` layout and toybox `mktemp` template boundary. It is bound
to HEAD `3901f085f182354cc7033f34cec8acb8507d192e`, staged tree
`a95623dfa420e596f4c9fe521088b7a02a4fc3e1`, and base
`5dff0c6a5c137331eb45d77ba4c2326dc01a0f4e`. The target produced 24/24
upstream terminal results (23 `OK`, one `EXPECTEDFAIL`) and one installed
production consumer flow passed 4/4 capability assertions: NativeWindow/OpenGLES2
presentation, OHAudio mixed non-zero callback data, dynrec guest execution, and
version identity. The transaction used one launch and owner-only release; an
independent readback found the task roots and PID absent. r171 and r172 remain
immutable diagnostic/history evidence and are not reused or combined with r178.
- Bind SpeexDSP 1.2.1, libslirp 4.9.3, and FluidSynth 2.5.7 because these are
  the currently published dependencies validated by W0.
- Use shared IIR1, opusfile, libpng, libslirp, FluidSynth, and mt32emu. Keep
  SDL2, zlib, SpeexDSP, and SDL2_net on their published static/default options.
- Repair only the consumer-generated `opusfile.pc` when the published Conan
  component does not expose its nested header directory. The recipe declares
  `libogg/1.3.5` directly, generates the ordinary provider file `ogg.pc`, and
  requires the unique ordered `Requires: ogg opus` edge. The repair validates
  the real header and `libopusfile.so` and rejects missing, duplicate,
  reordered, or unexpected provider edges.

## Source and test framework

The official GitHub release archive is pinned by SHA-256. It has no `.git`
directory, while `scripts/get-version.sh` requires Git metadata. The patch
falls back to the source root and requires `DOSBOX_SOURCE_GIT_HASH`; the recipe
binds that variable to the official `v0.82.2` tag commit prefix `f8c24`.

The 24 upstream tests require GoogleTest/GoogleMock. Their exact upstream
source archive and WrapDB patch are hash-pinned into Meson's package cache so
`wrap_mode=nodownload` remains deterministic during the build. The DOSBox,
GoogleTest, and WrapDB inputs are all locally present and match their pinned
SHA-256 values. Meson executes the test entries with one process to keep target
CPU use bounded.

## Test accounting

`tests/meson.build` registers exactly 24 independent entries. The intentional
failure example is still one Meson entry and passes only when Meson records its
expected-failure outcome as `EXPECTEDFAIL`. The other 23 entries require `OK`.
Assertions, sources, parameter values, and
shared/static repetitions are not counted as additional tests.

The installed-package check is one separate logical flow. It verifies that the
packaged `dosbox` executable exists, starts with `--version`, exits normally,
and reports upstream version 0.82.2. The current r178 flow additionally
observes the production NativeWindow/OpenGLES2, OHAudio mixer callback, and
dynrec guest sentinel boundaries; those four assertions remain internal to the
single consumer flow and are not counted as four independent test entries.

The recipe scans every archive patch during `export_sources` and scans the
patched source tree before framework seeding. Any preprocessing directive that
contains `OHOS` is a hard failure; source portability must use POSIX behavior
or capability detection instead of a platform-name branch.

## Remaining submission gates

1. Update the existing PR #6478 and Issue #1093 association from the current
   staged candidate tree after the blocking Pre-PR contract passes.
2. Run the blocking POST_CREATE Pre-PR contract against the updated tree.
3. Use a guarded non-force push on the exact task branch.
4. Process the platform AI Review for the new PR HEAD, fixing every real
   code issue and rerunning only directly affected validation.
5. Trigger the single current-HEAD CI only after Review. After CI passes, add
   the requested graphics, real audio, and dynrec guest-workload evidence,
   then rerun any contract/Review/CI gates invalidated by those changes before
   final submission.
