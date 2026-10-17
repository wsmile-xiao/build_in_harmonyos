// test_package for libmusicxml 3.22 — substantively exercises the C++ API.
//
// Covers the public interface in src/interface/libmusicxml.h:
//  1. library version string is non-empty
//  2. library version float is positive
//  3. musicxmlstring2guido converts a minimal score without error
//  4. the Guido output is non-empty
// Four checks total (R34: no empty-shell test).

#include <libmusicxml/libmusicxml.h>

#include <cstdio>
#include <cstring>
#include <sstream>
#include <string>

namespace {

const char* kMinimalScore =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    "<!DOCTYPE score-partwise PUBLIC \"-//Recordare//DTD MusicXML 3.1 Partwise//EN\" \"http://www.musicxml.org/dtds/partwise.dtd\">\n"
    "<score-partwise version=\"3.1\">\n"
    "  <part-list><score-part id=\"P1\"><part-name>Music</part-name></score-part></part-list>\n"
    "  <part id=\"P1\">\n"
    "    <measure number=\"1\">\n"
    "      <attributes>\n"
    "        <divisions>1</divisions>\n"
    "        <key><fifths>0</fifths></key>\n"
    "        <time><beats>4</beats><beat-type>4</beat-type></time>\n"
    "        <clef><sign>G</sign><line>2</line></clef>\n"
    "      </attributes>\n"
    "      <note><pitch><step>C</step><octave>4</octave></pitch>"
    "<duration>4</duration><type>whole</type></note>\n"
    "    </measure>\n"
    "  </part>\n"
    "</score-partwise>\n";

}  // namespace

int main() {
    int passed = 0;

    const char* versionStr = MusicXML2::musicxmllibVersionStr();
    if (versionStr == nullptr || std::strlen(versionStr) == 0) {
        std::fprintf(stderr, "FAIL: musicxmllibVersionStr is empty\n");
        return 1;
    }
    std::printf("CHECK 1 passed: lib version str=%s\n", versionStr);
    ++passed;

    float version = MusicXML2::musicxmllibVersion();
    if (!(version > 0.0f)) {
        std::fprintf(stderr, "FAIL: musicxmllibVersion not positive: %f\n", version);
        return 1;
    }
    std::printf("CHECK 2 passed: lib version float=%f\n", version);
    ++passed;

    std::ostringstream guido;
    MusicXML2::xmlErr err = MusicXML2::musicxmlstring2guido(kMinimalScore, true, guido);
    if (err != MusicXML2::kNoErr) {
        std::fprintf(stderr, "FAIL: musicxmlstring2guido returned err=%d\n", static_cast<int>(err));
        return 1;
    }
    std::printf("CHECK 3 passed: musicxmlstring2guido returned kNoErr\n");
    ++passed;

    std::string out = guido.str();
    if (out.empty()) {
        std::fprintf(stderr, "FAIL: guido output is empty\n");
        return 1;
    }
    std::printf("CHECK 4 passed: guido output bytes=%u\n", static_cast<unsigned>(out.size()));
    ++passed;

    std::printf("test_musicxml OK: %d/4 checks passed\n", passed);
    return 0;
}
