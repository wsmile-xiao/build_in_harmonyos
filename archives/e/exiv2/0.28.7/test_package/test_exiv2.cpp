// test_package/test_exiv2.cpp — substantive API test (R34)
//
// Verifies that the exiv2 library is correctly linked and functional by:
//   1. Querying the runtime version string via Exiv2::version()
//   2. Creating an ExifData container and writing an EXIF tag
//      ("Exif.Image.Make") via operator[] (the core metadata write API)
//   3. Reading the tag back and comparing its value
//
// If the exiv2 library were missing or broken, linking or the API call
// would fail — this is NOT a hollow "printf OK" test.

#include <exiv2/exiv2.hpp>

#include <cstdio>
#include <cstring>
#include <string>

int main(void) {
    // 1. Runtime version check — exercises Exiv2::version() symbol
    const char* ver = Exiv2::version();
    if (!ver || std::strlen(ver) == 0) {
        std::fprintf(stderr, "FAIL: Exiv2::version() returned empty\n");
        return 1;
    }
    std::printf("Exiv2 runtime version: %s\n", ver);

    // 2. Write EXIF metadata via the core API
    std::string make_value = "OpenHarmony-TestCam";
    Exiv2::ExifData exifData;
    exifData["Exif.Image.Make"] = make_value;

    // 3. Read it back and verify
    Exiv2::Exifdatum& md = exifData["Exif.Image.Make"];
    std::string read_back = md.toString();
    std::printf("Exif.Image.Make = %s (count=%zu)\n", read_back.c_str(), exifData.count());

    if (read_back != make_value) {
        std::fprintf(stderr, "FAIL: wrote '%s' but read back '%s'\n",
                     make_value.c_str(), read_back.c_str());
        return 1;
    }
    if (exifData.count() != 1) {
        std::fprintf(stderr, "FAIL: expected 1 EXIF entry, got %zu\n", exifData.count());
        return 1;
    }

    std::printf("test exiv2 0.28.7: OK\n");
    return 0;
}
