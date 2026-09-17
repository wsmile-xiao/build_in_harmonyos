// Consumer test for the installed libxspf package.
//
// Exercises the real public API the way applications use it: parse an XSPF
// v1 document from memory, inspect tracks/props through a reader callback,
// reject a malformed document, write a new playlist to memory and parse it
// back (round-trip). Every CHECK prints a PASS line; the first failure
// prints FAIL and exits non-zero, so the runner can report an exact count.
// Total CHECK count: 14 (kept in sync with the marker in conanfile.py).
#include <xspf/Xspf.h>
#include <xspf/XspfVersion.h>

#include <cstring>
#include <iostream>
#include <string>
#include <vector>

using namespace Xspf;

namespace {

int g_passed = 0;

#define XSPF_CHECK(cond, name)                                           \
    do {                                                                 \
        if (cond) {                                                      \
            ++g_passed;                                                  \
            std::cout << "XSPF-CHECK-PASS: " << name << std::endl;        \
        }                                                                \
        else {                                                           \
            std::cout << "XSPF-CHECK-FAIL: " << name << std::endl;        \
            return 1;                                                    \
        }                                                                \
    } while (0)

const char kBaseUri[] = "file:///playlist/sample.xspf";

const char kValidPlaylist[] =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    "<playlist version=\"1\" xmlns=\"http://xspf.org/ns/0/\">\n"
    "<title>HMBS sample</title>\n"
    "<trackList>\n"
    "<track>\n"
    "<title>First track</title>\n"
    "<location>file:///music/first.ogg</location>\n"
    "<duration>12345</duration>\n"
    "</track>\n"
    "<track>\n"
    "<title>Second track</title>\n"
    "<location>file:///music/second.ogg</location>\n"
    "</track>\n"
    "</trackList>\n"
    "</playlist>\n";

// Missing the mandatory trackList element is treated leniently by the
// reference parser (true-machine evidence 2026-09-15: parseMemory returns
// XSPF_READER_SUCCESS with zero tracks), so the rejection probe must use
// syntactically broken XML that Expat unconditionally rejects -- a
// truncated document with unclosed track/trackList/playlist elements.
const char kBrokenPlaylist[] =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    "<playlist version=\"1\" xmlns=\"http://xspf.org/ns/0/\">\n"
    "<trackList>\n"
    "<track>\n"
    "<location>file:///music/broken.ogg</location>\n";

class CollectCallback : public XspfReaderCallback {
public:
    int version;
    std::vector<std::string> titles;
    std::vector<std::string> locations;

    CollectCallback() : version(-1) {}

protected:
    void addTrack(XspfTrack * track) {
        if (track == NULL) {
            return;
        }
        if (track->getTitle() != NULL) {
            titles.push_back(track->getTitle());
        }
        if (track->getLocationCount() > 0
                && track->getLocation(0) != NULL) {
            locations.push_back(track->getLocation(0));
        }
        delete track;
    }

    void setProps(XspfProps * props) {
        if (props != NULL) {
            version = props->getVersion();
            delete props;
        }
    }
};

} // namespace

int main() {
    // 1. Library version matches the adapted upstream release.
    XSPF_CHECK(XSPF_VER_MAJOR == 1 && XSPF_VER_MINOR == 2
            && XSPF_VER_RELEASE == 1,
            "version-macros-1.2.1");

    // 2-6. Parse a valid v1 playlist from memory.
    XspfReader reader;
    CollectCallback callback;
    int code = reader.parseMemory(kValidPlaylist,
            static_cast<int>(std::strlen(kValidPlaylist)), &callback,
            kBaseUri);
    XSPF_CHECK(code == XSPF_READER_SUCCESS, "parse-valid-memory");
    XSPF_CHECK(callback.titles.size() == 2, "track-count-is-2");
    XSPF_CHECK(callback.titles[0] == "First track", "first-track-title");
    XSPF_CHECK(callback.locations.size() == 2
            && callback.locations[1] == "file:///music/second.ogg",
            "second-track-location");
    XSPF_CHECK(callback.version == 1, "playlist-version-is-1");

    // 7. Truncated/malformed XML must not parse cleanly.
    CollectCallback broken;
    int brokenCode = reader.parseMemory(kBrokenPlaylist,
            static_cast<int>(std::strlen(kBrokenPlaylist)), &broken,
            kBaseUri);
    XSPF_CHECK(brokenCode != XSPF_READER_SUCCESS, "reject-missing-tracklist");

    // 8. Write a new playlist to memory and check the serialised bytes.
    XspfIndentFormatter formatter;
    int writerError = 0;
    XspfWriter * writer = XspfWriter::makeWriter(formatter, kBaseUri,
            XspfWriter::NO_XML_BASE, &writerError);
    XSPF_CHECK(writer != NULL && writerError == 0, "writer-created");
    XspfProps props;
    props.giveTitle("Round trip", XspfData::COPY);
    XSPF_CHECK(writer->setProps(props), "writer-set-props");
    XspfTrack track;
    track.giveTitle("Written track", XspfData::COPY);
    track.giveAppendLocation("file:///music/written.ogg", XspfData::COPY);
    track.setDuration(999);
    XSPF_CHECK(writer->addTrack(track), "writer-add-track");
    char * memory = NULL;
    int numBytes = 0;
    XSPF_CHECK(writer->writeMemory(memory, numBytes) == XSPF_WRITER_SUCCESS
            && memory != NULL && numBytes > 0,
            "writer-write-memory");
    bool carriesTitle = std::strstr(memory, "Written track") != NULL;
    XSPF_CHECK(carriesTitle, "written-bytes-carry-title");
    delete writer;

    // 9-10. The bytes we just wrote must parse back with the same title.
    CollectCallback roundTrip;
    int roundCode = reader.parseMemory(memory, numBytes, &roundTrip,
            kBaseUri);
    XSPF_CHECK(roundCode == XSPF_READER_SUCCESS, "round-trip-parse");
    XSPF_CHECK(roundTrip.titles.size() == 1
            && roundTrip.titles[0] == "Written track",
            "round-trip-title-intact");
    delete[] memory;

    std::cout << "XSPF-TEST-SUMMARY: passed=" << g_passed
              << " total=14" << std::endl;
    return 0;
}
