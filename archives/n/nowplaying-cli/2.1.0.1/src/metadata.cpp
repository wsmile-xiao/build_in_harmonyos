/*
 * Copyright (c) 2026 nowplaying-cli OHOS equivalent port.
 * Licensed under the MIT License.
 *
 * metadata.cpp — demo metadata model + JSON serialization.
 */

#include "metadata.h"

#include <cinttypes>
#include <cstdio>

namespace npc {

const char* const kKeyTitle = "title";
const char* const kKeyArtist = "artist";
const char* const kKeyAlbum = "album";
const char* const kKeyComposer = "composer";
const char* const kKeyGenre = "genre";
const char* const kKeyDurationSec = "durationSec";
const char* const kKeyElapsedSec = "elapsedSec";
const char* const kKeyPlaybackRate = "playbackRate";
const char* const kKeyTrackNumber = "trackNumber";
const char* const kKeyPlaybackState = "playbackState";

const std::vector<const char*> kGetFields = {
    kKeyTitle, kKeyArtist, kKeyAlbum, kKeyComposer, kKeyGenre,
    kKeyDurationSec, kKeyElapsedSec, kKeyPlaybackRate,
    kKeyTrackNumber, kKeyPlaybackState,
};

std::string JsonEscape(const std::string& in) {
    std::string out;
    out.reserve(in.size() + 8);
    for (unsigned char c : in) {
        switch (c) {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b";  break;
            case '\f': out += "\\f";  break;
            case '\n': out += "\\n";  break;
            case '\r': out += "\\r";  break;
            case '\t': out += "\\t";  break;
            default:
                if (c < 0x20) {
                    char buf[8];
                    std::snprintf(buf, sizeof(buf), "\\u%04x", c);
                    out += buf;
                } else {
                    out += static_cast<char>(c);
                }
        }
    }
    return out;
}

std::string FormatFieldLine(const std::string& key, const std::string& value) {
    return key + "\t" + value + "\n";
}

std::string MetadataToJson(const Metadata& m) {
    char buf[64];
    std::string json = "{";
    bool first = true;
    auto addStr = [&](const char* k, const std::string& v) {
        if (!first) json += ", ";
        first = false;
        json += std::string("\"") + k + "\": \"" + JsonEscape(v) + "\"";
    };
    auto addInt = [&](const char* k, int64_t v) {
        if (!first) json += ", ";
        first = false;
        std::snprintf(buf, sizeof(buf), "%" PRId64, v);
        json += std::string("\"") + k + "\": " + buf;
    };
    auto addDouble = [&](const char* k, double v) {
        if (!first) json += ", ";
        first = false;
        std::snprintf(buf, sizeof(buf), "%.6f", v);
        json += std::string("\"") + k + "\": " + buf;
    };

    addStr(kKeyTitle, m.title);
    addStr(kKeyArtist, m.artist);
    addStr(kKeyAlbum, m.album);
    addStr(kKeyComposer, m.composer);
    addStr(kKeyGenre, m.genre);
    addInt(kKeyDurationSec, m.durationSec);
    addInt(kKeyElapsedSec, m.elapsedSec);
    addDouble(kKeyPlaybackRate, m.playbackRate);
    addInt(kKeyTrackNumber, m.trackNumber);
    addStr(kKeyPlaybackState, m.playbackState);
    json += "}";
    return json;
}

Metadata DemoMetadata() {
    Metadata m;
    m.title = "Demo Track (OHOS)";
    m.artist = "nowplaying-cli port";
    m.album = "OpenHarmony AVSession Demo";
    m.composer = "kirtan-shah/nowplaying-cli (upstream)";
    m.genre = "Demo";
    m.durationSec = 240;
    m.elapsedSec = 42;
    m.playbackRate = 1.0;
    m.trackNumber = 1;
    m.playbackState = "playing";
    return m;
}

} // namespace npc