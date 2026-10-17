// test_package consumer test for libvpd 2.2.11.
// Exercises real public APIs only (no private headers/symbols):
//   1. C++ API: lsvpd::System() default ctor + pack()/unpack() round-trip
//      (pure in-memory VPD tree serialisation, hardware-independent,
//      observable via non-empty packed buffer and round-trip field equality).
//   2. C API:   new_vpdretriever(NULL,NULL) public entry point called and
//      released; returns NULL when no VPD db exists (expected on this host)
//      without crashing, which still proves the symbol links and runs.
#include <cstdio>
#include <cstring>

#include <libvpd-2/system.hpp>

extern "C" {
#include <libvpd-2/vpdretriever.h>
}

int main() {
    // --- C++ API: System pack/unpack round-trip (real data path) ---
    lsvpd::System sys;
    void *buf = nullptr;
    unsigned int len = sys.pack(&buf);
    if (len == 0 || buf == nullptr) {
        std::fprintf(stderr, "FAIL: lsvpd::System::pack returned empty buffer\n");
        return 1;
    }
    std::printf("lsvpd::System::pack -> %u bytes (machineType='%s')\n",
                len, sys.getMachineType().c_str());

    // unpack into a fresh System and verify the round-trip object is usable
    lsvpd::System unpacked;
    unpacked.unpack(buf);
    delete[] static_cast<char *>(buf);

    // machineType must match across the round trip
    if (unpacked.getMachineType() != sys.getMachineType()) {
        std::fprintf(stderr, "FAIL: pack/unpack round-trip mismatch\n");
        return 1;
    }
    std::printf("pack/unpack round-trip OK (machineType='%s', serial1='%s')\n",
                unpacked.getMachineType().c_str(),
                unpacked.getSerial1().c_str());

    // --- C API: public entry point links and runs ---
    struct vpdretriever *r = new_vpdretriever(NULL, NULL);
    if (r != NULL) {
        free_vpdretriever(r);
        std::printf("new_vpdretriever(NULL,NULL) -> allocated, freed OK\n");
    } else {
        std::printf("new_vpdretriever(NULL,NULL) -> NULL (no VPD db on this host), API executed OK\n");
    }

    std::printf("test_libvpd: ALL OK\n");
    return 0;
}