/*
 * Copyright (c) 2026 nowplaying-cli OHOS equivalent port.
 * Licensed under the MIT License.
 *
 * main.cpp — CLI entry point. Mirrors the upstream nowplaying-cli
 * (kirtan-shah/nowplaying-cli, macOS Foundation/MediaRemote) subcommands
 * exactly so that scripts that drive `nowplaying-cli` keep working when
 * moved to OpenHarmony PC.
 *
 * Subcommands:
 *   get [field...] [--json] [--demo]
 *   get-raw [--demo]
 *   play | pause | togglePlayPause | next | previous
 *   seek <secs>
 *   --help / -h / help
 *
 * Exit codes: 0 on success, 1 on user error or missing playback.
 */

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

#include "avsession_helper.h"
#include "metadata.h"

namespace {
constexpr const char* kVersion = "2.1.0.1";

const std::vector<std::string> kSupportedFields = {
    "title", "artist", "album", "composer", "genre",
    "durationSec", "duration", "elapsedSec", "elapsedTime", "playbackRate",
    "trackNumber", "playbackState", "isPlaying", "isPaused",
};

void PrintHelp(const char* prog) {
    std::cout
        << "Usage: " << prog << " <subcommand> [options]\n"
        << "\n"
        << "OHOS AVSession equivalent of nowplaying-cli (2.1.0.1).\n"
        << "Under the hood this binary acts as an AVSession *provider*\n"
        << "(OH_AVSession / OH_AVMetadataBuilder) — see README.md \"API gap\".\n"
        << "\n"
        << "Subcommands:\n"
        << "  get [title artist album composer genre duration elapsedTime\n"
        << "       playbackRate trackNumber ...] [--json] [--demo]\n"
        << "      Print one or more now-playing fields (one per line in TSV\n"
        << "      format, or as a JSON object with --json). With no fields,\n"
        << "      prints all known fields. Use --demo to seed the in-process\n"
        << "      provider with DemoMetadata before printing.\n"
        << "  get-raw [--demo]\n"
        << "      Alias for `get --json` (full record as raw JSON, sanitized).\n"
        << "  play\n"
        << "      Resume playback.\n"
        << "  pause\n"
        << "      Pause playback.\n"
        << "  togglePlayPause\n"
        << "      Toggle between play and pause.\n"
        << "  next\n"
        << "      Skip to the next track.\n"
        << "  previous\n"
        << "      Skip to the previous track.\n"
        << "  seek <secs>\n"
        << "      Seek to <secs> seconds in the current track.\n"
        << "  --help / -h / help\n"
        << "      Show this help.\n"
        << "  --version / -v / version\n"
        << "      Show version.\n"
        << "\n"
        << "Options (accepted with `get` / `get-raw`):\n"
        << "  --json   Emit a single JSON object instead of per-field lines.\n"
        << "  --demo   (Re)seed the local provider session with demo metadata\n"
        << "           before executing the query.\n"
        << "\n"
        << "Environment:\n"
        << "  NOWPLAYING_CLI_OHOS_DEMO=1  Implies --demo.\n"
        << "\n"
        << "Notes (OHOS API gap):\n"
        << "  The native OHOS SDK (libohavsession.so, 115 symbols) exposes\n"
        << "  only the provider surface (OH_AVSession_*, OH_AVMetadataBuilder)\n"
        << "  and the AVCast controller. There is no native\n"
        << "  OH_AVSessionManager / OH_AVSessionController / getAllSession-\n"
        << "  Descriptors(); controller queries live only in the ETS/JS\n"
        << "  AVSessionKit. Wire avsession_helper::ControllerBridge to an ETS\n"
        << "  bridge when a native controller API ships (see avsession_helper.h).\n"
        << std::flush;
}

void PrintVersion() {
    std::cout << "nowplaying-cli " << kVersion
              << " (OHOS AVSession equivalent port)\n"
              << "upstream: kirtan-shah/nowplaying-cli 2.1.0 (macOS)\n";
}

std::string FieldValue(const npc::Metadata& m, const std::string& field) {
    if (field == "title")       return m.title;
    if (field == "artist")      return m.artist;
    if (field == "album")       return m.album;
    if (field == "composer")    return m.composer;
    if (field == "genre")       return m.genre;
    if (field == "durationSec") return std::to_string(m.durationSec);
    if (field == "duration")    return std::to_string(m.durationSec);
    if (field == "elapsedSec")  return std::to_string(m.elapsedSec);
    if (field == "elapsedTime") return std::to_string(m.elapsedSec);
    if (field == "playbackRate") {
        char buf[32];
        std::snprintf(buf, sizeof(buf), "%.6f", m.playbackRate);
        return buf;
    }
    if (field == "trackNumber")  return std::to_string(m.trackNumber);
    if (field == "playbackState") return m.playbackState;
    if (field == "isPlaying")  return (m.playbackState == "playing") ? "true" : "false";
    if (field == "isPaused")   return (m.playbackState == "paused")  ? "true" : "false";
    return "";
}

// --json flag or get-raw: single JSON object
void PrintJson(const npc::Metadata& m) {
    std::cout << npc::MetadataToJson(m) << "\n";
}

// Default `get` (no --json): label\tvalue per requested field
void PrintTsv(const npc::Metadata& m, const std::vector<std::string>& fields) {
    const std::vector<std::string> toPrint =
        fields.empty() ? std::vector<std::string>{
                             "title", "artist", "album", "composer", "genre",
                             "durationSec", "elapsedSec", "playbackRate",
                             "trackNumber", "playbackState"}
                       : fields;
    for (const auto& f : toPrint) {
        std::cout << npc::FormatFieldLine(f, FieldValue(m, f));
    }
}

// `get` exit behaviour: if no track is present, print nothing and exit 1
// (upstream: when MRMediaRemoteGetNowPlayingInfo returns nil).
bool HasTrack(const npc::Metadata&) { return true; }

bool FileExists(const std::string& field) {
    return std::find(kSupportedFields.begin(), kSupportedFields.end(), field) !=
           kSupportedFields.end();
}

}  // namespace

int main(int argc, char* argv[]) {
    const char* prog = argc > 0 ? argv[0] : "nowplaying-cli";

    if (argc < 2) {
        // Upstream: no args → get (print all)
        argc = 2;
        argv[0] = const_cast<char*>(prog);
        argv[1] = const_cast<char*>("get");
        argv[2] = nullptr;
    }

    std::string sub = argv[1];
    if (sub == "--help" || sub == "-h" || sub == "help") {
        PrintHelp(prog);
        return 0;
    }
    if (sub == "--version" || sub == "-v" || sub == "version") {
        PrintVersion();
        return 0;
    }

    // Create a local provider session once per process. The session persists
    // for the lifetime of the process (and for the test harness that runs
    // `get --demo` followed by `get` in a sequence, the demo data is kept in
    // the in-process cache inside avsession_helper).
    bool demoRequested = (std::getenv("NOWPLAYING_CLI_OHOS_DEMO") != nullptr);
    for (int i = 2; i < argc; ++i) {
        if (std::strcmp(argv[i], "--demo") == 0) demoRequested = true;
    }
    std::string sessionErr;
    npc::Session* session = npc::CreateSession("nowplaying-cli-demo-session", &sessionErr);
    if (demoRequested) {
        npc::Metadata demo = npc::DemoMetadata();
        npc::SetMetadata(session, demo, nullptr);
        npc::SetPlaybackState(session, demo.playbackState, demo.elapsedSec,
                              demo.playbackRate, nullptr);
    }

    // -----------------------------------------------------------------
    // get / get-raw
    // -----------------------------------------------------------------
    if (sub == "get" || sub == "get-raw") {
        bool wantJson = (sub == "get-raw");
        std::vector<std::string> fields;
        for (int i = 2; i < argc; ++i) {
            std::string tok = argv[i];
            if (tok == "--json") wantJson = true;
            else if (tok == "--demo") { /* handled above */ }
            else if (tok.rfind("--", 0) == 0) {
                std::cerr << "Unknown option: " << tok << "\n";
                return 1;
            } else {
                if (!FileExists(tok) &&
                    tok != "--json" && tok != "--demo") {
                    // Mirror upstream: unknown field prints empty value
                }
                fields.push_back(tok);
            }
        }

        if (sub == "get-raw" && !fields.empty()) {
            std::cerr << "get-raw accepts no extra fields\n";
            return 1;
        }

        npc::Metadata m;
        std::string getErr;
        npc::GetSessionMetadata(session, &m, &getErr);

        if (wantJson) {
            PrintJson(m);
        } else {
            PrintTsv(m, fields);
        }
        npc::DestroySession(session);
        return 0;
    }

    // -----------------------------------------------------------------
    // Playback controls
    // -----------------------------------------------------------------
    npc::Metadata cur;
    std::string curErr;
    npc::GetSessionMetadata(session, &cur, &curErr);
    int rc = 0;
    std::string dispatchErr;

    auto dispatch = [&](npc::ControllerBridge::Command cmd, int64_t seekSec) -> int {
        std::string err;
        npc::Result r = npc::ControllerBridge::Dispatch(
            session, cmd, seekSec, cur.playbackState, &cur, &err);
        if (r != npc::Result::kOk) {
            std::cerr << "command failed: " << err << "\n";
            return 1;
        }
        return 0;
    };

    if (sub == "play") {
        rc = dispatch(npc::ControllerBridge::Command::kPlay, 0);
    } else if (sub == "pause") {
        rc = dispatch(npc::ControllerBridge::Command::kPause, 0);
    } else if (sub == "togglePlayPause") {
        rc = dispatch(npc::ControllerBridge::Command::kTogglePlayPause, 0);
    } else if (sub == "next") {
        rc = dispatch(npc::ControllerBridge::Command::kNext, 0);
    } else if (sub == "previous") {
        rc = dispatch(npc::ControllerBridge::Command::kPrevious, 0);
    } else if (sub == "seek") {
        if (argc < 3) {
            std::cerr << "Usage: " << prog << " seek <secs>\n";
            rc = 1;
        } else {
            char* end = nullptr;
            double secs = std::strtod(argv[2], &end);
            if (end == argv[2] || secs < 0) {
                std::cerr << "Invalid seek value: " << argv[2] << "\n";
                rc = 1;
            } else {
                rc = dispatch(npc::ControllerBridge::Command::kSeek,
                              static_cast<int64_t>(secs));
            }
        }
    } else {
        std::cerr << "Unknown subcommand: " << sub << "\n"
                  << "Run `" << prog << " --help` for usage.\n";
        rc = 1;
    }

    npc::DestroySession(session);
    return rc;
}