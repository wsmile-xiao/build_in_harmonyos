# nowplaying-cli — OpenHarmony (OHOS) equivalent port

**Version:** 2.1.0.1 · **Upstream:** [kirtan-shah/nowplaying-cli](https://github.com/kirtan-shah/nowplaying-cli) 2.1.0 (macOS)

An OpenHarmony PC native (arm64) equivalent of the macOS-only `nowplaying-cli`
tool, implemented in **pure C++17** against the **OHOS native AVSessionKit**
provider API (`libohavsession.so`). The CLI surface (subcommands, field names,
TSV/JSON output, help text, exit codes) is kept identical to upstream so that
scripts written against the macOS tool keep working on OHOS.

## Why an equivalent port (API gap)

The upstream tool is Objective-C and depends on `Foundation`, `AppKit` and the
private `MediaRemote` framework. Those do not exist in the OHOS SDK (no
`libobjc` / `libdispatch` / `Foundation/Foundation.h`), so a source-port is not
possible (`env_unsupported`). Instead this project provides a **functional
equivalent** built on the native AVSessionKit.

Verified against the native SDK shipped with `ohos-sdk_26.0.0.18`:

| Capability | Native SDK (C API) | ETS/JS (ArkTS) |
|---|---|---|
| Create session (provider role) | `OH_AVSession_Create` ✅ | ✅ |
| Publish metadata | `OH_AVMetadataBuilder_*` + `OH_AVSession_SetAVMetadata` ✅ | ✅ |
| Publish playback state / seek | `OH_AVSession_SetPlaybackState` / `SetPlaybackPosition` ✅ | ✅ |
| Register control callbacks | `OH_AVSession_RegisterCommandCallback` ✅ | ✅ |
| **Query system "now playing" (controller role)** | **❌ not present** | `getAllSessionDescriptors()` / `getAVSessionController()` / `getAVPlaybackState()` / `getAVMetadata()` / `sendControlCommand()` ✅ |
| Screen-cast control | `OH_AVCastController_*` (SendCommonCommand/SendSeekCommand/...) ✅ | ✅ |

`libohavsession.so` exports only **115 symbols** — all provider-side plus the
AVCast (screen-cast) controller. There is **no native manager/controller**
(`OH_AVSessionManager`, `OH_AVSessionController`,
`getAllSessionDescriptors`): a full `grep` of the SDK headers confirms only
8 AVSession headers ship with the native SDK, none of them controller-side.

**Consequence:** the native side can only play the *provider* role. This port
therefore:

1. Creates its own AVSession (`OH_AVSession_Create`, audio type) and publishes
   metadata/playback state through the provider pipeline — a faithful demo of
   the full native AVSession path (`get --demo` seeds and reads it back).
2. Leaves an explicit **controller bridge stub**
   (`avsession_helper.h::ControllerBridge`) that the CLI routes all control
   commands (`play/pause/togglePlayPause/next/previous/seek`) through. Today it
   drives the local provider session; when a native controller API ships (or
   an ETS bridge is added), only that one function needs to change.

## Build

```bash
cmake -B build \
  -DCMAKE_TOOLCHAIN_FILE=<SDK>/native/build/cmake/ohos.toolchain.cmake \
  -DOHOS_ARCH=arm64 -DOHOS_PLATFORM=OHOS -DCMAKE_BUILD_TYPE=Release
cmake --build build -j2
# binary: build/nowplaying-cli
```

Requires: OHOS native SDK ≥ 26 (AVSessionKit C API, `SystemCapability.
Multimedia.AVSession.Core`), CMake ≥ 3.16, C++17 clang toolchain.

## Usage

```
nowplaying-cli get [title artist album composer genre duration elapsedTime
                    playbackRate trackNumber ...] [--json] [--demo]
nowplaying-cli get-raw [--demo]
nowplaying-cli play | pause | togglePlayPause | next | previous
nowplaying-cli seek <secs>
nowplaying-cli --help | --version
```

* `get` — prints the requested fields, one per line in `field<TAB>value` TSV
  format (no fields = all fields). `--json` prints one JSON object.
* `get-raw` — same as `get --json` (full sanitized record).
* `play` / `pause` / `togglePlayPause` / `next` / `previous` / `seek <secs>` —
  control commands routed through `ControllerBridge`.
* `--demo` (or env `NOWPLAYING_CLI_OHOS_DEMO=1`) seeds the in-process provider
  with demo metadata before the query, so output is meaningful even where the
  AVSession system service is not reachable (headless CI, shell-only).

Exit codes: `0` success, `1` user error / command failure.

## Differences from upstream

* Language: C++17 (upstream: Objective-C). No `.m`/`.mm`/`.swift`.
* Backend: OHOS AVSessionKit provider API (upstream: private MediaRemote).
* `get`/`get-raw` read the provider session this binary owns (demo mode), not
  the system-wide "now playing" player — the native controller API is absent
  (see table above). An ETS bridge / future native controller API plugs into
  `ControllerBridge::Dispatch`.
* Field set is a documented subset of upstream's (most commonly scripted
  fields: title/artist/album/composer/genre/duration/elapsedTime/playbackRate/
  trackNumber/playbackState plus isPlaying/isPaused aliases).

## Files

```
CMakeLists.txt          CMake ≥3.16, C++17, links libohavsession
src/main.cpp            CLI entry, argument parsing, help, exit codes
src/avsession_helper.{h,cpp}  OH_AVSession provider wrapper + ControllerBridge stub
src/metadata.{h,cpp}    metadata model, TSV/JSON serialization, demo data
```

## License

MIT (same as upstream).
