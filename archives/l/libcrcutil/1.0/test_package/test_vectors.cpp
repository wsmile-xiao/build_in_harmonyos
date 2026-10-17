#include <interface.h>

#include <cstddef>
#include <cstdio>

namespace {

using crcutil_interface::CRC;
using crcutil_interface::UINT64;

struct TestVector {
    std::size_t size;
    UINT64 expected;
};

const TestVector kVectors[] = {
    { 0, 0x00000000ULL}, { 1, 0xcbf4f86aULL}, { 2, 0x0e0135ebULL},
    { 3, 0x4af6657fULL}, { 4, 0xdd15b0edULL}, { 5, 0x2fcf3031ULL},
    { 6, 0x5e52f696ULL}, { 7, 0xa2facab6ULL}, { 8, 0x2c62a338ULL},
    { 9, 0x3cd77d0eULL}, {10, 0xa86b024dULL}, {11, 0xc75d81cbULL},
    {12, 0x47cf5c8fULL}, {13, 0x8e2e73c5ULL}, {14, 0x6500b086ULL},
    {15, 0x26fec18eULL}, {16, 0x91bf2e92ULL}, {17, 0x239522d2ULL},
    {18, 0xcbc6ed34ULL}, {19, 0x1f8c4c80ULL}, {20, 0x7b95985cULL},
    {21, 0x68b6c46bULL}, {22, 0x6752b86dULL}, {23, 0xa6af057aULL},
    {24, 0x4f9c41eaULL}, {25, 0x6899a830ULL}, {26, 0xe2bf09a4ULL},
    {27, 0x79a2db27ULL}, {28, 0x79d1f583ULL}, {29, 0x13ba3a55ULL},
    {30, 0x5188e767ULL}, {31, 0xac95cb05ULL}, {32, 0x1246ff04ULL},
    {33, 0x81b5b4c8ULL}, {34, 0x8d464179ULL}, {35, 0x61b8d6d6ULL},
    {36, 0x2d45a106ULL}, {37, 0xa7ea3b1aULL}, {38, 0x32fb10e2ULL},
    {39, 0x904785cdULL}, {40, 0x0b60ba12ULL}, {41, 0x3dc9514dULL},
    {42, 0x1e7faed3ULL}, {43, 0x78403287ULL}, {44, 0xf1183e4eULL},
};

UINT64 referenceCrc32c(const unsigned char *data, std::size_t size) {
    UINT64 crc = 0xffffffffULL;
    for (std::size_t index = 0; index < size; ++index) {
        crc ^= data[index];
        for (unsigned int bit = 0; bit < 8; ++bit) {
            const UINT64 mask = 0ULL - (crc & 1ULL);
            crc = (crc >> 1) ^ (0x82f63b78ULL & mask);
        }
    }
    return (crc ^ 0xffffffffULL) & 0xffffffffULL;
}

}  // namespace

int main() {
    const UINT64 polynomial_lo = 0x82f63b78ULL;
    const UINT64 polynomial_hi = 0;
    const std::size_t degree = 32;
    const bool canonical = true;
    CRC *crc = CRC::Create(polynomial_lo, polynomial_hi, degree, canonical,
                           0, 0, 0, false, NULL);
    if (crc == NULL) {
        std::fputs("[fail] CRC32C vector engine was not created\n", stderr);
        return 1;
    }

    unsigned char data[44] = {};
    for (std::size_t case_index = 0;
         case_index < sizeof(kVectors) / sizeof(kVectors[0]); ++case_index) {
        const TestVector &vector = kVectors[case_index];
        for (std::size_t index = 0; index < vector.size; ++index) {
            data[index] = static_cast<unsigned char>(
                (index * 37 + vector.size * 11) & 0xff);
        }

        const UINT64 reference = referenceCrc32c(data, vector.size);
        if (reference != vector.expected) {
            std::fprintf(stderr,
                         "[fail] reference CRC32C vector %zu: expected %08llx, got %08llx\n",
                         case_index, vector.expected, reference);
            crc->Delete();
            return static_cast<int>(case_index + 2);
        }

        UINT64 actual = 0;
        crc->Compute(data, vector.size, &actual);
        if (actual != vector.expected) {
            std::fprintf(stderr,
                         "[fail] CRC32C vector %zu: expected %08llx, got %08llx\n",
                         case_index, vector.expected, actual);
            crc->Delete();
            return static_cast<int>(case_index + 2);
        }
        std::printf("[ok] CRC32C vector %zu\n", case_index);
    }

    crc->Delete();
    std::puts("[ok] installed-library CRC32C vectors: 45/45 passed");
    return 0;
}
