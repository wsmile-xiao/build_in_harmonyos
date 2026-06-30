/* test_package for libqxp 0.0.1 — Conan L1 smoke test
 *
 * Verifies that the libqxp library is correctly installed and its API
 * symbols can be resolved at link time. Calls QXPDocument::isSupported()
 * with an empty stream to exercise the real API.
 */
#include <libqxp/libqxp.h>
#include <librevenge-stream/librevenge-stream.h>
#include <cstdio>
#include <cstdlib>

int main(void) {
    /* Create an empty input stream via librevenge-stream.
     * isSupported() should return false for empty/invalid input. */
    const unsigned char empty_data[] = { 0 };
    librevenge::RVNGStringStream stream(empty_data, 0);

    libqxp::QXPDocument::Type type = libqxp::QXPDocument::TYPE_UNKNOWN;
    bool supported = libqxp::QXPDocument::isSupported(&stream, &type);

    if (!supported) {
        printf("test libqxp 0.0.1: OK (isSupported returned false for empty input)\n");
        return 0;
    }

    fprintf(stderr, "test libqxp 0.0.1: FAIL (empty input unexpectedly supported)\n");
    return 1;
}
