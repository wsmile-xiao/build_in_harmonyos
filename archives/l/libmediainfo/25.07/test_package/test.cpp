// test_package/test.cpp — consumer-side functional test for libmediainfo
//
// Parses the official MediaArea "Example.ogg" regression sample (embedded
// as base64 below, 4855 bytes, from MediaInfoLib Release/Example.ogg) with
// the MediaInfo C++ API and asserts the extracted metadata matches the
// upstream reference values (Ogg container, Vorbis audio, VBR mode,
// Unicode tag round-trip).  This exercises the real parsing path: Ogg
// container reader + Vorbis stream parser + tag handling + XML output.
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>

#include "MediaInfo/MediaInfo.h"
#include "ZenLib/Ztring.h"

namespace {

// MediaInfoLib Release/Example.ogg — official Unicode test sample
// ("Test for Unicode (UTF-8)", Vorbis in Ogg, VBR).
const char* EXAMPLE_OGG_B64 =
    "T2dnUwACAAAAAAAAAACdRgAAAAAAAI2A0TcBHgF2b3JiaXMAAAAAAkSsAAAAAAAAA/QBAAAAAAC4AU9nZ1MAAAAAAAAAAAAAnUYA"
    "AAEAAABqICKtEf//Sf//////////////////A3ZvcmJpcx0AAABYaXBoLk9yZyBsaWJWb3JiaXMgSSAyMDAzMDMwOAkAAAAeAAAA"
    "VElUTEU9VGVzdCBmb3IgVW5pY29kZSAoVVRGLTgpNQAAAEFSQUJJQz3Yptin2KjYqdiq2KvYrNit2K7Yr9iw2LHYstiz2LTYtdi2"
    "2LfYuNi52LrZgNmBOQAAAEhFQlJFVz3XkNeR15LXk9eU15XXlteX15jXmdea15vXnNed157Xn9eg16HXotej16TXpdem1rDWsSQA"
    "AABDT01CSU5FUlM9y4bLh8uJy5jLmcuay5vLnMyAzIHMg8yJzKMlAAAAQ1lSSUxMSUM90IHQgtCD0ITQhdCG0IfQiNCJ0IrQi9CM"
    "0I7QjyMAAABFTkdMSVNIPWFiY2RlZmdoYWlqa2xtbm9wcXJzdHV2d3h5ejIAAABGUkVOQ0g9YcOgw6TDosOlw6HDo8Omw4XDhiBj"
    "w6fDhyBlw6nDqMOrw6ogdcO5w7zDuzgAAABHUkVFSz3Osc6yzrPOtM61zrbOt864zrnOus67zrzOvc6+zr/PgM+Bz4LPg8+Ez4XP"
    "hs+Hz4jPiZQAAABMQVRJTj3EgMSBxILEg8SExIXEhsSHxIjEicSKxIvEjMSNxI7Ej8SQxJHEksSTxJTElcSWxJfEmMSZxJrEm8Sc"
    "xJ3EnsSfxKDEocSixKPEpMSlxKbEp8SoxKnEqsSrxKzErcSuxK/EsMSxxLLEs8S0xLXEtsS3xLjEucS6xLvEvMS9xL7Ev8WAxYHF"
    "gsWDxYTFhcWGAQV2b3JiaXMpQkNWAQAIAACAIkwgw4DQkFUAABAAAICoNhRrqbHWGmOhKEbUYmoxxhhj4yxGkGKLMcYYY4wxxhhj"
    "jDHGGGMgNGQVAAAEAEAx6hWTnkLMOefcGKaNUdopxznn3BjFiTBYIaW5pZpSzKGTnErKOeccCA1ZBQAAAgBASCGFFFJIIYUUUkgh"
    "hRRSSimllGKKKaaYYooppphyzDHHHIMMMuikk0466SSkkEIJpaSSUkqtxRpr7733nnvvvffee++9995777333nvPOQdCQ1YBACAA"
    "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";

std::string b64decode(const std::string& in) {
    static const std::string tbl =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string out;
    out.reserve(in.size() * 3 / 4);
    int val = 0, valb = -8;
    for (unsigned char c : in) {
        size_t i = tbl.find(c);
        if (i == std::string::npos) continue;
        val = (val << 6) + static_cast<int>(i);
        valb += 6;
        if (valb >= 0) {
            out.push_back(static_cast<char>((val >> valb) & 0xFF));
            valb -= 8;
        }
    }
    return out;
}

} // namespace

int main(int argc, char** argv) {
    using namespace MediaInfoLib;

    // Write the embedded official sample to a temp file.  Prefer the
    // caller-provided path; otherwise derive a writable temp location
    // from TMPDIR (portable across OHOS device, CI worker and Linux
    // hosts) and fail loudly when the sample cannot be written.
    std::string path;
    if (argc > 1) {
        path = argv[1];
    } else {
        const char* tmpdir = std::getenv("TMPDIR");
        path = std::string(tmpdir ? tmpdir : "/tmp") + "/mi_tp_example.ogg";
    }
    {
        std::ofstream f(path.c_str(), std::ios::binary);
        if (!f.is_open()) {
            std::fprintf(stderr, "FAIL: cannot open %s for writing\n", path.c_str());
            return 1;
        }
        f << b64decode(EXAMPLE_OGG_B64);
        f.flush();
        if (!f.good()) {
            std::fprintf(stderr, "FAIL: error writing sample to %s\n", path.c_str());
            return 1;
        }
    }

    // 1) Parse with the full MediaInfo pipeline.
    MediaInfo MI;
    if (!MI.Open(ZenLib::Ztring(path.c_str()).To_Unicode())) {
        std::fprintf(stderr, "FAIL: MediaInfo::Open failed for %s\n", path.c_str());
        return 1;
    }
    String format = MI.Get(Stream_General, 0, __T("Format"));
    if (format != __T("Ogg")) {
        std::fprintf(stderr, "FAIL: expected container Format 'Ogg', got '%s'\n",
                     ZenLib::Ztring(format).To_UTF8().c_str());
        return 1;
    }
    std::printf("OK: container Format=Ogg\n");

    // 2) Audio track parsed through the Vorbis parser.
    if (MI.Count_Get(Stream_Audio) < 1) {
        std::fprintf(stderr, "FAIL: expected at least one audio stream\n");
        return 1;
    }
    String afmt = MI.Get(Stream_Audio, 0, __T("Format"));
    if (afmt != __T("Vorbis")) {
        std::fprintf(stderr, "FAIL: expected audio Format 'Vorbis', got '%s'\n",
                     ZenLib::Ztring(afmt).To_UTF8().c_str());
        return 1;
    }
    String mode = MI.Get(Stream_General, 0, __T("OverallBitRate_Mode"));
    if (mode != __T("VBR")) {
        std::fprintf(stderr, "FAIL: expected OverallBitRate_Mode 'VBR', got '%s'\n",
                     ZenLib::Ztring(mode).To_UTF8().c_str());
        return 1;
    }
    std::printf("OK: audio Format=Vorbis, OverallBitRate_Mode=VBR\n");

    // 3) Unicode tag round-trip (the sample title is multi-script).
    String title = MI.Get(Stream_General, 0, __T("Title"));
    std::string title8 = ZenLib::Ztring(title).To_UTF8();
    if (title8.find("Unicode") == std::string::npos) {
        std::fprintf(stderr, "FAIL: expected Unicode title, got '%s'\n", title8.c_str());
        return 1;
    }
    std::printf("OK: Unicode title round-trip: '%s'\n", title8.c_str());

    // 4) Inform() produces the full XML output tree (explicit XML format).
    MI.Option(__T("Inform"), __T("XML"));
    String inform = MI.Inform();
    std::string inform8 = ZenLib::Ztring(inform).To_UTF8();
    if (inform8.find("<track type=\"Audio\">") == std::string::npos
        || inform8.find("Vorbis") == std::string::npos) {
        std::fprintf(stderr, "FAIL: Inform() XML output incomplete\n");
        return 1;
    }
    std::printf("OK: Inform() XML output contains Audio track\n");

    // 5) Version string sanity (MediaInfoLib 25.07).
    String ver = MediaInfo::Option_Static(__T("Info_Version"));
    std::string ver8 = ZenLib::Ztring(ver).To_UTF8();
    if (ver8.find("25.07") == std::string::npos) {
        std::fprintf(stderr, "FAIL: Info_Version does not contain 25.07: '%s'\n", ver8.c_str());
        return 1;
    }
    std::printf("OK: Info_Version=%s\n", ver8.c_str());

    MI.Close();
    std::printf("mediainfo_test: ALL OK\n");
    return 0;
}
