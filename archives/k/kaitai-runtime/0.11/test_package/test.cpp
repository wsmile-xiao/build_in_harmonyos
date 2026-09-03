/* Consumer smoke test for kaitai-runtime 0.11 (Conan L1 test).
 *
 * Exercises the shipped runtime: kstream byte reading and bytes_to_str
 * encoding conversion (including the IBM437 -> CP437 alias path).
 */
#include <kaitai/kaitaistream.h>
#include <kaitai/kaitaistruct.h>
#include <cstdio>
#include <cstring>
#include <string>

int main(void) {
    // "ABC" as raw bytes via kstream
    unsigned char buf[4] = {'A', 'B', 'C', 0};
    kaitai::kstream ks(std::string((const char *)buf, 3));

    if (ks.read_bytes_full() != std::string("ABC")) {
        std::printf("FAIL: read_bytes_full\n");
        return 1;
    }

    // Encoding conversion: IBM437 bytes 0xCC 0xB2 -> UTF-8 U+2560 U+2593
    std::string ibm437("\xCC\xB2", 2);
    std::string utf8 = kaitai::kstream::bytes_to_str(ibm437, "IBM437");
    std::string expect("\xE2\x95\xA0\xE2\x96\x93", 6);
    if (utf8 != expect) {
        std::printf("FAIL: bytes_to_str IBM437 -> got %zu bytes\n", utf8.size());
        return 1;
    }

    std::printf("test kaitai-runtime 0.11: OK (stream + IBM437 encoding)\n");
    return 0;
}
