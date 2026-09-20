// SPDX-License-Identifier: BSD-2-Clause
// Test: verify ytmusic.h header and libytm.a are correctly packaged.
//
// This test checks:
// 1. ytmusic.h can be included
// 2. TESTED_YTMUSICAPI_VERSION constant is accessible
// 3. Core data structures are defined (meta::Thumbnail, search::Media, etc.)
// 4. The YTMusic class is declared

#include <audiotube/ytmusic.h>

#include <cassert>
#include <cstdio>
#include <string>
#include <type_traits>

// Keep runtime assertions active in Release builds (NDEBUG would strip them,
// turning the checks below into no-ops and giving false test confidence).
#undef NDEBUG
#include <cassert>

int main() {
    // Verify the tested ytmusicapi version constant
    std::string version(TESTED_YTMUSICAPI_VERSION);
    assert(!version.empty());
    printf("TESTED_YTMUSICAPI_VERSION: %s\n", version.c_str());

    // Verify core data structures are defined
    meta::Thumbnail thumb{"http://example.com/img.jpg", 100, 100};
    assert(thumb.url == "http://example.com/img.jpg");
    assert(thumb.width == 100);
    assert(thumb.height == 100);

    meta::Artist artist{"Test Artist", std::nullopt};
    assert(artist.name == "Test Artist");

    search::Media media;
    media.video_id = "dQw4w9WgXcQ";
    media.title = "Test Song";
    assert(media.video_id == "dQw4w9WgXcQ");
    assert(media.title == "Test Song");

    // Verify YTMusic class is declared with real members (not an empty stub).
    // YTMusic cannot be instantiated here (needs Python + pybind11::embed at
    // link time), so use compile-time type traits instead: sizeof() > 0 is
    // always true for any complete type and verifies nothing, while is_empty
    // actually fails if YTMusic were replaced by an empty placeholder class.
    static_assert(std::is_class<YTMusic>::value, "YTMusic must be a class type");
    static_assert(!std::is_empty<YTMusic>::value, "YTMusic must not be an empty class");

    printf("All audiotube ytm library tests passed!\n");
    return 0;
}
