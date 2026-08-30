# SDL2 2.32.10 adaptation notes

## Scope

This dependency exists only to close the native multimedia gap in DOSBox
Staging Issue #1093. The candidate adds an OHAudio output driver and a
NativeWindow EGL/GLES2 video driver while retaining dummy/offscreen drivers
only for the upstream portable test suite.

## Source and build evidence

- Official archive SHA-256: `5f5993c530f084535c65a6879e9b26ad441169b3e25d789d83287040a9ca5165`.
- All 16 generated patches apply in order to a fresh official source tree;
  Git, GNU patch with zero fuzz, and Conan patch-ng replay are bound below.
- A Windows-host SDK 20 cross-build compiled 641/641 build edges. This is
  build-only evidence and does not establish target execution.
- Capability-link probes pass only with the complete OHAudio or
  NativeWindow/EGL/GLES2 provider set; removing any required provider fails
  before producing an ELF.
- Source and patch conditionals whose macro name contains `OHOS`: zero.

## Runtime boundary

- Upstream CTest inventory contains 16 registered containers. The automation
  container registers 308 cases, of which 300 are applicable and 8 are
  upstream-disabled; the remaining 15 containers make the logical target
  denominator 315.
- Native audio requires exact `ohaudio` selection plus callback, frame, and
  non-silent sample progress. The native callback never waits for producer
  data; Start runs outside the backend mutex, and callback storage is released
  only after successful Stop/Release and active-callback drain.
- Native video requires an ArkUI-created surface in the same process and
  ordinary `SDL_CreateWindow` creation through the `nativewindow` driver. The
  consumer additionally requires the accelerated `opengles2` renderer,
  texture upload, four-color readback, and `SDL_RenderPresent`.
- SDL's generic Unix EGL loader defaults to versioned desktop names such as
  `libGLESv2.so.2`. The API 20 NativeWindow provider exposes the unversioned
  SONAMEs `libGLESv2.so` and `libEGL.so`, so the NativeWindow driver selects
  the same unversioned loader contract as the other embedded EGL backends.
- The NativeWindow backend provides native output only; its event pump does
  not claim keyboard, mouse, or touch input integration.
- NativeWindow resolves GLES entry points through the context-bound
  `eglGetProcAddress` before the generic loader fallback. This avoids selecting
  same-named ABI stubs from an unversioned provider export when the target EGL
  version is opaque or older than 1.5.
- The current target transaction `task4328-param4-148108-r104-controller-consumers-only-hdc40504`
  completed the four native consumers (`4/4 PASS`) on `10.62.148.108:2222`.
  It is explicitly consumer-only: its upstream field is `0/0 NOT_RUN`, while
  the immutable predecessor `task4328-param4-148108-a70` supplies the separate
  `315/315` upstream proof. These denominators must not be merged or relabeled.

## Current target evidence

- Terminal summary: `F:/HarmonyPC/issue-1093-sdl2-2.32.10-native/w3-r104-terminal-pass-release-summary.json`
  (SHA-256 `59b3fa43e765eb5c4378350a80301d5c6d5d0daebca6ee41b78990bf8bedee9a`).
- W3 result: `PASS_W3_TRANSACTION`, one launch, WAL 21 records, release and
  post-release both PASS, and no task-owned process or root remained.
- Hilog records the production operations: `core_pass` (17 assertions),
  `invalid_pass` (14 cases), `audio_pass` with `ohaudio` callbacks and frames,
  and `video_pass` with `nativewindow`/`opengles2` texture readback and present.
- Snapshot is `NOT_REQUIRED`; it is an observer policy field and is not part of
  the four-consumer denominator.

## Package metadata

The installed `sdl2.pc` prefix is rewritten to `${pcfiledir}/../..`. Static
metadata propagates `ohaudio`, `native_window`, `EGL`, `GLESv2`, `m`, and
`pthread`; shared packages retain private provider DT_NEEDED entries. The
shared build keeps a static core only for upstream CTest and removes that core
and its target metadata from the installed shared package.
