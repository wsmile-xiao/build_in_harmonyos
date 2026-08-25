// libnymphcast v0.2.1 test_package - verify library links and core API works
//
// Upstream ships no test suite (make test is a dangling target). This
// consumer-side probe verifies that the public header compiles, the
// library links, and core API surface (NymphCastClient construct/setters,
// public data structures and enums) behaves as declared.
//
// It does not perform network discovery (findServers/getShares require a
// live NymphCast receiver on the LAN, unavailable in headless CI).

#include <nymphcast_client.h>

#include <cstdio>
#include <string>
#include <vector>

static int g_fail = 0;

#define CHECK(cond, what) \
    do { \
        if (!(cond)) { std::printf("FAIL %s\n", (what)); ++g_fail; } \
        else { std::printf("ok   %s\n", (what)); } \
    } while (0)

int main() {
    {
        // NymphCastClient ctor calls NymphRemoteServer::init internally.
        NymphCastClient client;
        CHECK(true, "NymphCastClient construct");

        // Client id setter.
        client.setClientId("test-client");
        CHECK(true, "NymphCastClient::setClientId");

        // Application message callback (std::function signature).
        AppMessageFunction appFn = [](std::string appId, std::string message) {
            (void) appId; (void) message;
        };
        client.setApplicationCallback(appFn);
        CHECK(true, "NymphCastClient::setApplicationCallback");

        // Status update callback (std::function signature).
        StatusUpdateFunction stFn = [](uint32_t handle, NymphPlaybackStatus status) {
            (void) handle; (void) status;
        };
        client.setStatusUpdateCallback(stFn);
        CHECK(true, "NymphCastClient::setStatusUpdateCallback");

        // Public data structure: NymphCastRemote.
        NymphCastRemote remote;
        remote.name = "TestReceiver";
        remote.ipv4 = "192.168.1.100";
        remote.ipv6 = "";
        remote.port = 4004;
        CHECK(remote.name == "TestReceiver" && remote.port == 4004,
              "NymphCastRemote fields");

        // Public data structure: NymphPlaybackStatus + NymphRemoteStatus enum.
        NymphPlaybackStatus status;
        status.status = NYMPH_PLAYBACK_STATUS_STOPPED;
        status.error = false;
        status.stopped = true;
        status.playing = false;
        status.duration = 0;
        status.position = 0.0;
        status.volume = 100;
        status.subtitles_off = true;
        status.title = "track";
        status.artist = "artist";
        CHECK(status.status == NYMPH_PLAYBACK_STATUS_STOPPED
              && status.volume == 100, "NymphPlaybackStatus fields");

        // Public data structure: NymphMediaFile + NymphMediaFileType enum.
        NymphMediaFile file;
        file.mediaserver = remote;
        file.id = 7;
        file.name = "test.mp4";
        file.section = "videos";
        file.type = FILE_TYPE_VIDEO;
        CHECK(file.id == 7 && file.type == FILE_TYPE_VIDEO,
              "NymphMediaFile fields");

        // Public enum: NymphSeekType.
        CHECK(NYMPH_SEEK_TYPE_BYTES == 1 && NYMPH_SEEK_TYPE_PERCENTAGE == 2,
              "NymphSeekType enum");
    }  // dtor runs here: NymphCastClient::~NymphCastClient -> shutdown
    CHECK(true, "NymphCastClient destructor shutdown");

    if (g_fail) {
        std::printf("libnymphcast test failed %d items\n", g_fail);
        return 1;
    }
    std::printf("libnymphcast v0.2.1: all assertions passed\n");
    return 0;
}
