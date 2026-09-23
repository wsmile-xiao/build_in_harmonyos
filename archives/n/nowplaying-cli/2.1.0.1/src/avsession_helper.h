/*
 * Copyright (c) 2026 nowplaying-cli OHOS equivalent port.
 * Licensed under the MIT License.
 *
 * avsession_helper.h — thin C++ wrapper around the OpenHarmony native
 * AVSessionKit provider API (libohavsession.so).
 *
 * API-gap note (verified against the native SDK shipped with
 * ohos-sdk 26.0.0.18):
 *   * Headers available: native_avsession.h, native_avmetadata.h,
 *     native_avplaybackstate.h, native_avqueueitem.h,
 *     native_avsession_base.h, native_avcastcontroller.h, ... (8 total)
 *   * libohavsession.so exports 115 symbols — all provider-side
 *     (OH_AVSession_Create/SetAVMetadata/SetPlaybackState/...) plus the
 *     AVCast (screen-cast) controller (OH_AVCastController_*).
 *   * NOT present at native level: AVSessionManager,
 *     OH_AVSessionController, getAllSessionDescriptors(),
 *     getAVPlaybackState(), getAVMetadata() (controller query side).
 *     Those exist only in the ETS/JS API
 *     (@ohos.multimedia.avsession.d.ts).
 *
 * This helper therefore implements the *provider* role: create an AVSession,
 * publish metadata + playback state, and register command callbacks so a
 * head-unit / AVCast receiver can drive us. The CLI commands
 * play/pause/togglePlayPause/next/previous/seek map onto this provider
 * surface (plus a documented OH_AVCastController_SendCommonCommand stub for
 * the cast scenario).
 */

#ifndef NOWPLAYING_CLI_AVSESSION_HELPER_H
#define NOWPLAYING_CLI_AVSESSION_HELPER_H

#include <string>

#include "metadata.h"

namespace npc {

// Opaque provider session handle.
struct Session;

enum class Result {
    kOk = 0,
    kApiUnavailable,  // AVSession service not reachable at runtime
    kCreateFailed,
    kSetMetadataFailed,
    kSetStateFailed,
    kSetPositionFailed,
    kInvalidArgument,
};

// Create + activate an audio AVSession. sessionTag should be the calling
// bundle/app name (e.g. "com.example.nowplaying-cli").
// Returns a heap Session that must be released with DestroySession().
Session* CreateSession(const std::string& sessionTag, std::string* err);

void DestroySession(Session* s);

// Publish metadata on the session (provider demo path:
// OH_AVMetadataBuilder -> OH_AVSession_SetAVMetadata).
Result SetMetadata(Session* s, const Metadata& m, std::string* err);

// Publish playback state (playing/paused/stopped + position + speed).
Result SetPlaybackState(Session* s, const std::string& state, int64_t elapsedSec,
                        double rate, std::string* err);

// Seek: OH_AVSession_SetPlaybackPosition(elapsedSec) on the provider.
Result Seek(Session* s, int64_t elapsedSec, std::string* err);

// Read back the metadata the provider published (OH_AVMetadata getters).
// When no live session exists the caller falls back to DemoMetadata().
Result GetSessionMetadata(Session* s, Metadata* out, std::string* err);

// ---------------------------------------------------------------------------
// Controller bridge stub (documented gap):
//
//   Upstream nowplaying-cli *controls* the system "now playing" player from
//   the outside (MediaRemote MRMediaRemoteSendCommand). In the native OHOS
//   SDK there is no controller object; the ETS/JS side has
//   `avSession.getAVSessionController(sessionId)` + sendControlCommand().
//   A future ETS bridge (or a native controller API once shipped) should
//   implement the functions below; the CLI already calls them through
//   ControllerBridge::Dispatch(). Today, in provider/demo mode, they are
//   routed back into the local provider session (the session this binary
//   owns), which keeps the CLI surface identical to upstream.
// ---------------------------------------------------------------------------
struct ControllerBridge {
    // Command names match upstream nowplaying-cli subcommands.
    enum class Command { kPlay, kPause, kTogglePlayPause, kNext, kPrevious, kSeek };

    // Execute a control command. In provider/demo mode this drives the local
    // session; add ETS-bridge dispatch here when a native controller API
    // becomes available.
    static Result Dispatch(Session* s, Command cmd, int64_t seekSec,
                           const std::string& currentState, Metadata* stateOut,
                           std::string* err);
};

} // namespace npc

#endif // NOWPLAYING_CLI_AVSESSION_HELPER_H