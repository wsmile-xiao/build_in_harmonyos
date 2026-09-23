#include <interface.h>

#include <cstddef>
#include <cstdio>

namespace {

using crcutil_interface::CRC;
using crcutil_interface::UINT64;

int check(bool condition, int code, const char *message) {
    if (!condition) {
        std::fprintf(stderr, "[fail] %s\n", message);
        return code;
    }
    return 0;
}

}  // namespace

int main() {
    static const unsigned char data[] = "abcdefgh";
    const UINT64 polynomial_lo = 0x82f63b78ULL;
    const UINT64 polynomial_hi = 0;
    const std::size_t degree = 32;
    const bool canonical = true;
    const UINT64 roll_start_value_lo = 0x2222ULL;
    const UINT64 roll_start_value_hi = 0;
    const std::size_t roll_window_bytes = 4;
    CRC *crc = CRC::Create(polynomial_lo, polynomial_hi, degree, canonical,
                           roll_start_value_lo, roll_start_value_hi,
                           roll_window_bytes, false, NULL);
    int result = check(crc != NULL, 1, "CRC::Create returned NULL");
    if (result != 0) {
        return result;
    }

    UINT64 polynomial = 0;
    crc->GeneratingPolynomial(&polynomial);
    if ((result = check(polynomial == 0x82f63b78ULL, 2,
                        "generating polynomial mismatch")) != 0 ||
        (result = check(crc->Degree() == 32, 3, "degree mismatch")) != 0 ||
        (result = check(crc->RollWindowBytes() == 4, 4,
                        "rolling window mismatch")) != 0) {
        crc->Delete();
        return result;
    }

    UINT64 one_shot = 0;
    crc->Compute(data, sizeof(data) - 1, &one_shot);
    if ((result = check(one_shot == 0x0a9421b7ULL, 5,
                        "CRC32C known vector mismatch")) != 0) {
        crc->Delete();
        return result;
    }

    UINT64 incremental = 0;
    // Compute extends the INOUT CRC value, as specified by the public API.
    crc->Compute(data, 3, &incremental);
    crc->Compute(data + 3, sizeof(data) - 1 - 3, &incremental);
    if ((result = check(incremental == one_shot, 6,
                        "incremental CRC mismatch")) != 0) {
        crc->Delete();
        return result;
    }

    UINT64 rolling = 0;
    crc->RollStart(data, &rolling);
    UINT64 direct = 0x2222ULL;
    crc->Compute(data, 4, &direct);
    if ((result = check(rolling == direct, 7,
                        "rolling CRC start mismatch")) != 0) {
        crc->Delete();
        return result;
    }

    crc->Roll(data[0], data[4], &rolling);
    direct = 0x2222ULL;
    crc->Compute(data + 1, 4, &direct);
    result = check(rolling == direct, 8, "rolling CRC update mismatch");
    crc->Delete();
    if (result != 0) {
        return result;
    }

    std::puts("[ok] libcrcutil installed-library consumer: 8/8 checks passed");
    return 0;
}
