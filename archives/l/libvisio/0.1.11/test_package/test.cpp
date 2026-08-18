// test.cpp — Consumer test for libvisio 0.1.11
// Verifies that the libvisio library can be linked and its API called.
// R34: Test must substantively depend on the tested package.

#include <libvisio/libvisio.h>
#include <libvisio/VisioDocument.h>
#include <librevenge-stream/RVNGStreamImplementation.h>

#include <cstdio>

int main() {
    // Create a minimal RVNGStringStream with dummy data
    const unsigned char data[] = {0x00, 0x01, 0x02, 0x03};
    librevenge::RVNGStringStream stream(data, 4);

    // Call libvisio API: VisioDocument::isSupported
    // This should return false for non-Visio data
    bool result = libvisio::VisioDocument::isSupported(&stream);

    if (result) {
        fprintf(stderr, "FAIL: isSupported returned true for dummy data\n");
        return 1;
    }

    printf("PASS: libvisio API call succeeded, isSupported() = false\n");
    return 0;
}
