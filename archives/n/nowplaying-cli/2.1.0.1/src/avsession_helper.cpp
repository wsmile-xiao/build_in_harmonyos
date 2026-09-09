/*
 * Copyright (c) 2026 nowplaying-cli OHOS equivalent port.
 * Licensed under the MIT License.
 *
 * avsession_helper.cpp — OpenHarmony AVSessionKit provider wrapper.
 *
 * Runtime note: the AVSession service (distributed_sched + avsession
 * subsystem) may not be reachable in a headless build/CI shell. Every
 * call into libohavsession.so therefore degrades gracefully: on failure the
 * CLI falls back to its in-process demo state (DemoMetadata) so that
 * `nowplaying-cli get --demo` / `get-raw` still produce meaningful output
 * identical in shape to upstream.
 */

#include "avsession_helper.h"

#include <cstdint>
#include <cstring>
#include <mutex>

// OpenHarmony native AVSessionKit provider API.
// Use fully-qualified sysroot paths rather than bare filenames: the OHOS SDK
// default sysroot is <HNP>/ohos/native/sysroot/usr/include (searched
// automatically via the OHOS SDK clang with/without explicit --sysroot), and
// the AVSession headers live in the subdir multimedia/av_session/.
// Bare "native_avsession.h" with a matching -I only worked when the
// project's CMakeLists injected the subdir into the include path; the Conan
// CMakeToolchain flow does not currently inject it, so prefer the qualified
// form which works everywhere without extra search paths.
#include <multimedia/av_session/native_avsession.h>
#include <multimedia/av_session/native_avmetadata.h>
#include <multimedia/av_session/native_avplaybackstate.h>
#include <multimedia/av_session/native_avsession_base.h>

namespace npc {

namespace {

// Last state the CLI published/derived (works even when the AVSession
// service is unreachable). Guarded by gStateMutex.
std::mutex gStateMutex;
Metadata gCurrent;
bool gStateInitialized = false;

AVSession_PlaybackState StateToEnum(const std::string& state) {
    if (state == "playing") return PLAYBACK_STATE_PLAYING;
    if (state == "paused")  return PLAYBACK_STATE_PAUSED;
    if (state == "stopped") return PLAYBACK_STATE_STOPPED;
    return PLAYBACK_STATE_INITIAL;
}

const char* EnumToStateStr(AVSession_PlaybackState s) {
    switch (s) {
        case PLAYBACK_STATE_PLAYING: return "playing";
        case PLAYBACK_STATE_PAUSED:  return "paused";
        case PLAYBACK_STATE_STOPPED: return "stopped";
        case PLAYBACK_STATE_PREPARING: return "preparing";
        case PLAYBACK_STATE_COMPLETED: return "completed";
        default: return "initial";
    }
}

}  // namespace

struct Session {
    OH_AVSession* avsession = nullptr;
    std::string tag;
};

Session* CreateSession(const std::string& sessionTag, std::string* err) {
    OH_AVSession* raw = nullptr;
    // provider role: an app owning playback creates a session. bundleName /
    // abilityName are required by the native API; we pass the tag itself as a
    // stand-in so the call is well-formed even outside an app sandbox.
    AVSession_ErrCode rc = OH_AVSession_Create(
        SESSION_TYPE_AUDIO, sessionTag.c_str(),
        "nowplaying-cli", "MainAbility", &raw);
    if (rc != AV_SESSION_ERR_SUCCESS || raw == nullptr) {
        if (err) {
            char buf[128];
            std::snprintf(buf, sizeof(buf),
                          "OH_AVSession_Create failed (rc=%d); AVSession "
                          "service may be unavailable in this environment",
                          static_cast<int>(rc));
            *err = buf;
        }
        return nullptr;
    }
    // Activate is best-effort; failure is not fatal for a CLI demo.
    OH_AVSession_Activate(raw);
    Session* s = new Session;
    s->avsession = raw;
    s->tag = sessionTag;
    return s;
}

void DestroySession(Session* s) {
    if (!s) return;
    if (s->avsession) {
        OH_AVSession_Deactivate(s->avsession);
        OH_AVSession_Destroy(s->avsession);
    }
    delete s;
}

Result SetMetadata(Session* s, const Metadata& m, std::string* err) {
    {
        std::lock_guard<std::mutex> lock(gStateMutex);
        gCurrent = m;
        gStateInitialized = true;
    }
    if (!s || !s->avsession) {
        return Result::kOk;  // demo mode: in-process state only
    }
    OH_AVMetadataBuilder* builder = nullptr;
    if (OH_AVMetadataBuilder_Create(&builder) != AVMETADATA_SUCCESS || !builder) {
        if (err) *err = "OH_AVMetadataBuilder_Create failed";
        return Result::kSetMetadataFailed;
    }
    OH_AVMetadataBuilder_SetTitle(builder, m.title.c_str());
    OH_AVMetadataBuilder_SetArtist(builder, m.artist.c_str());
    OH_AVMetadataBuilder_SetAlbum(builder, m.album.c_str());
    OH_AVMetadataBuilder_SetComposer(builder, m.composer.c_str());
    OH_AVMetadataBuilder_SetAuthor(builder, m.composer.c_str());
    OH_AVMetadataBuilder_SetDuration(builder, m.durationSec * 1000);
    OH_AVMetadata* meta = nullptr;
    if (OH_AVMetadataBuilder_GenerateAVMetadata(builder, &meta) != AVMETADATA_SUCCESS ||
        !meta) {
        OH_AVMetadataBuilder_Destroy(builder);
        if (err) *err = "OH_AVMetadataBuilder_GenerateAVMetadata failed";
        return Result::kSetMetadataFailed;
    }
    AVSession_ErrCode rc = OH_AVSession_SetAVMetadata(s->avsession, meta);
    OH_AVMetadata_Destroy(meta);
    OH_AVMetadataBuilder_Destroy(builder);
    if (rc != AV_SESSION_ERR_SUCCESS) {
        if (err) {
            char buf[128];
            std::snprintf(buf, sizeof(buf),
                          "OH_AVSession_SetAVMetadata failed (rc=%d)", rc);
            *err = buf;
        }
        return Result::kSetMetadataFailed;
    }
    return Result::kOk;
}

Result SetPlaybackState(Session* s, const std::string& state, int64_t elapsedSec,
                        double rate, std::string* err) {
    {
        std::lock_guard<std::mutex> lock(gStateMutex);
        gCurrent.playbackState = state;
        gCurrent.elapsedSec = elapsedSec;
        gCurrent.playbackRate = rate;
        gStateInitialized = true;
    }
    if (!s || !s->avsession) return Result::kOk;

    AVSession_ErrCode rc = OH_AVSession_SetPlaybackState(s->avsession, StateToEnum(state));
    if (rc != AV_SESSION_ERR_SUCCESS) {
        if (err) {
            char buf[128];
            std::snprintf(buf, sizeof(buf),
                          "OH_AVSession_SetPlaybackState failed (rc=%d)", rc);
            *err = buf;
        }
        return Result::kSetStateFailed;
    }
    return Seek(s, elapsedSec, err);
}

Result Seek(Session* s, int64_t elapsedSec, std::string* err) {
    {
        std::lock_guard<std::mutex> lock(gStateMutex);
        gCurrent.elapsedSec = elapsedSec;
        gStateInitialized = true;
    }
    if (!s || !s->avsession) return Result::kOk;
    AVSession_PlaybackPosition pos{};
    pos.elapsedTime = elapsedSec * 1000;  // ms
    pos.updateTime = 0;
    AVSession_ErrCode rc = OH_AVSession_SetPlaybackPosition(s->avsession, &pos);
    if (rc != AV_SESSION_ERR_SUCCESS) {
        if (err) {
            char buf[128];
            std::snprintf(buf, sizeof(buf),
                          "OH_AVSession_SetPlaybackPosition failed (rc=%d)", rc);
            *err = buf;
        }
        return Result::kSetPositionFailed;
    }
    return Result::kOk;
}

Result GetSessionMetadata(Session* s, Metadata* out, std::string* err) {
    std::lock_guard<std::mutex> lock(gStateMutex);
    if (gStateInitialized) {
        *out = gCurrent;
        return Result::kOk;
    }
    // No in-process state yet: fall back to demo data.
    *out = DemoMetadata();
    return Result::kOk;
}

Result ControllerBridge::Dispatch(Session* s, Command cmd, int64_t seekSec,
                                  const std::string& currentState, Metadata* stateOut,
                                  std::string* err) {
    Metadata m;
    GetSessionMetadata(s, &m, nullptr);

    switch (cmd) {
        case Command::kPlay:
            m.playbackState = "playing";
            break;
        case Command::kPause:
            m.playbackState = "paused";
            break;
        case Command::kTogglePlayPause:
            m.playbackState = (currentState == "playing") ? "paused" : "playing";
            break;
        case Command::kNext: {
            // Upstream nowplaying-cli sends MRMediaRemoteCommandNextTrack; the
            // provider demo advances the track counter.
            m.trackNumber += 1;
            m.title = "Demo Track (OHOS) #" + std::to_string(m.trackNumber);
            m.elapsedSec = 0;
            m.playbackState = "playing";
            break;
        }
        case Command::kPrevious: {
            m.trackNumber = (m.trackNumber > 1) ? m.trackNumber - 1 : 1;
            m.title = "Demo Track (OHOS) #" + std::to_string(m.trackNumber);
            m.elapsedSec = 0;
            m.playbackState = "playing";
            break;
        }
        case Command::kSeek:
            m.elapsedSec = seekSec;
            break;
    }

    // Provider path: publish state/metadata to the AVSession service.
    // Cast scenario note: OH_AVCastController_SendCommonCommand /
    // OH_AVCastController_SendSeekCommand exist for the *screen-cast* side
    // (OH_AVSession_CreateAVCastController); a local non-cast session uses the
    // provider Set* calls. See avsession_helper.h "Controller bridge stub".
    Result r = SetMetadata(s, m, err);
    if (r != Result::kOk) return r;
    r = SetPlaybackState(s, m.playbackState, m.elapsedSec, m.playbackRate, err);
    if (r != Result::kOk) return r;
    if (stateOut) *stateOut = m;
    return Result::kOk;
}

}  // namespace npc