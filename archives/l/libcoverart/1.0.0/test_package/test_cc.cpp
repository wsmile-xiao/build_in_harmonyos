// Consumer test for the libcoverart C++ API (offline).
//
// Exercises construction, the offline Version()/LastResult()/
// LastHTTPCode()/LastErrorMessage() accessors and the proxy setters without
// any network traffic. Each CHECK prints exactly one PASS: or FAIL: line.
#include <cstdio>
#include <string>

#include "coverart/CoverArt.h"

static int passed = 0;
static int failed = 0;

#define CHECK(cond, label) do { \
    if (cond) { std::printf("PASS: %s\n", label); passed++; } \
    else { std::printf("FAIL: %s\n", label); failed++; } } while (0)

int main()
{
    CoverArtArchive::CCoverArt ca("hmbs-test-1.0");

    CHECK(ca.Version() == "libcoverart-v1.0.0",
          "Version() returns libcoverart-v1.0.0");
    CHECK(ca.LastResult() == CoverArtArchive::CCoverArt::eCoverArt_Success,
          "LastResult() is eCoverArt_Success before any fetch");
    CHECK(ca.LastHTTPCode() == 200,
          "LastHTTPCode() is 200 before any fetch");
    CHECK(ca.LastErrorMessage().empty(),
          "LastErrorMessage() is empty before any fetch");

    // Proxy setters are pure local state; they must not crash and must not
    // disturb the pre-fetch result state.
    ca.SetProxyHost("proxy.example");
    ca.SetProxyPort(8080);
    ca.SetProxyUserName("user");
    ca.SetProxyPassword("secret");
    CHECK(ca.LastResult() == CoverArtArchive::CCoverArt::eCoverArt_Success,
          "LastResult() unchanged after proxy setup");
    CHECK(ca.LastHTTPCode() == 200,
          "LastHTTPCode() unchanged after proxy setup");

    CoverArtArchive::CCoverArt other("other-app-2.5");
    CHECK(other.Version() == "libcoverart-v1.0.0",
          "second instance Version() returns libcoverart-v1.0.0");
    CHECK(other.LastErrorMessage().empty(),
          "second instance LastErrorMessage() is empty");

    std::printf("RESULT: %d passed, %d failed\n", passed, failed);
    return failed ? 1 : 0;
}
