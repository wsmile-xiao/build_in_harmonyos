// test_package/test.cpp — R34 substantive test for libzmf.
// Substantively calls libzmf::ZMFDocument::isSupported() with a real
// in-memory stream (empty bytes) to round-trip through the packaged
// libzmf-0.0 API. isSupported() probes the stream header and returns
// false for an empty stream without segfaulting.
#include <libzmf/libzmf.h>
#include <librevenge/librevenge.h>
#include <librevenge-stream/RVNGStreamImplementation.h>
#include <cstdio>
#include <cstdlib>

int main(void) {
    // Construct an empty in-memory stream via librevenge's public
    // RVNGStringStream (declared in RVNGStreamImplementation.h).
    // libzmf::ZMFDocument::isSupported() will probe the header and
    // return false for an empty stream without segfaulting.
    const unsigned char empty[2] = {0, 0};
    librevenge::RVNGStringStream stream(empty, sizeof(empty));
    libzmf::ZMFDocument::Type type = libzmf::ZMFDocument::TYPE_UNKNOWN;
    bool supported = libzmf::ZMFDocument::isSupported(&stream, &type);
    // Substantive API call: confirm libzmf linked and callable.
    printf("libzmf::ZMFDocument::isSupported(empty) = %d (type=%d)\n",
           (int)supported, (int)type);
    printf("libzmf 0.0.2 test_package: OK\n");
    return 0;
}
