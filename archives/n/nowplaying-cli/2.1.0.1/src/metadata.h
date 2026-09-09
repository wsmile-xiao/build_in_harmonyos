/*
 * Copyright (c) 2026 nowplaying-cli OHOS equivalent port.
 *
 * Licensed under the MIT License.
 *
 * metadata.h — demo metadata model + JSON serialization for the OHOS
 * equivalent port of nowplaying-cli.
 *
 * The upstream (kirtan-shah/nowplaying-cli, macOS) reads the "now playing"
 * track via the private MediaRemote framework. OpenHarmony's native
 * AVSessionKit (libohavsession.so, syscap SystemCapability.Multimedia
 * .AVSession.Core) does NOT expose a native controller API
 * (no OH_AVSessionManager / OH_AVSessionController / getAllSessionDescriptors);
 * that capability currently exists only in the ETS/JS AVSessionKit
 * (@ohos.multimedia.avsession.d.ts). Therefore this port plays the role of an
 * AVSession *provider* (the app that owns playback) and demonstrates the
 * full metadata/playback pipeline through the native provider API:
 *
 *   OH_AVSession_Create + OH_AVMetadataBuilder + OH_AVSession_SetAVMetadata
 *
 * The `get`/`get-raw` subcommands read the metadata of the provider session
 * this binary created (falling back to --demo data when the AVSession service
 * is not reachable, e.g. in headless CI). A controller stub point is left in
 * getMetadata (see ControllerBridge comment) so an ETS bridge or future
 * native controller API can be plugged in without changing the CLI surface.
 */

#ifndef NOWPLAYING_CLI_METADATA_H
#define NOWPLAYING_CLI_METADATA_H

#include <cstdint>
#include <map>
#include <string>
#include <vector>

namespace npc {

// Field keys — kept identical to the upstream nowplaying-cli `get` output,
// so scripts written against upstream keep working.
extern const char* const kKeyTitle;        // "title"
extern const char* const kKeyArtist;       // "artist"
extern const char* const kKeyAlbum;        // "album"
extern const char* const kKeyComposer;     // "composer"
extern const char* const kKeyGenre;        // "genre"
extern const char* const kKeyDurationSec;  // "durationSec"
extern const char* const kKeyElapsedSec;   // "elapsedSec"
extern const char* const kKeyPlaybackRate; // "playbackRate"
extern const char* const kKeyTrackNumber;  // "trackNumber"
extern const char* const kKeyPlaybackState;// "playbackState"

// Ordered list of fields as printed by upstream `nowplaying-cli get`
// (informational subset — upstream prints many more; we cover the most
// commonly scripted ones).
extern const std::vector<const char*> kGetFields;

// Parsed metadata record (provider session mirror).
struct Metadata {
    std::string title;
    std::string artist;
    std::string album;
    std::string composer;
    std::string genre;
    int64_t durationSec = 0;   // seconds
    int64_t elapsedSec = 0;    // seconds
    double playbackRate = 1.0; // 0.0 means stopped/paused
    int64_t trackNumber = 0;
    std::string playbackState; // "playing" | "paused" | "stopped" ...

    bool empty() const { return title.empty() && artist.empty() && album.empty(); }
};

// JSON escape (RFC 8259) — same semantics as upstream's sanitize logic.
std::string JsonEscape(const std::string& in);

// Serialize one field line: `<key>\t<value>` (upstream `get` format).
std::string FormatFieldLine(const std::string& key, const std::string& value);

// Render the full metadata as { "key": "value", ... } JSON object
// (upstream `get-raw` format, sorted keys for stable output).
std::string MetadataToJson(const Metadata& m);

// Demo dataset used when no live provider session exists (headless/CI).
Metadata DemoMetadata();

} // namespace npc

#endif // NOWPLAYING_CLI_METADATA_H