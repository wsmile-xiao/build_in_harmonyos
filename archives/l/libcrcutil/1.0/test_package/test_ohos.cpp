#include <interface.h>

#include <cstddef>
#include <cstdio>

#if !defined(__OHOS__)
#error "test_ohos must be compiled by the OHOS toolchain"
#endif

#if !defined(__aarch64__)
#error "test_ohos must target AArch64"
#endif

int main() {
    using crcutil_interface::CRC;
    using crcutil_interface::UINT64;

    // The public interface reports false on non-x86 targets.
    if (CRC::IsSSE42Available()) {
        std::fputs("[fail] x86 SSE4.2 reported on OHOS AArch64\n", stderr);
        return 1;
    }

    const UINT64 polynomial_lo = 0x82f63b78ULL;
    const UINT64 polynomial_hi = 0;
    const std::size_t degree = 32;
    const bool canonical = true;
    CRC *crc = CRC::Create(polynomial_lo, polynomial_hi, degree, canonical,
                           0, 0, 0, true, NULL);
    if (crc == NULL) {
        std::fputs("[fail] portable fallback was not created\n", stderr);
        return 2;
    }

    static const char vector[] = "abcdefgh";
    UINT64 value = 0;
    crc->Compute(vector, sizeof(vector) - 1, &value);
    crc->Delete();
    if (value != 0x0a9421b7ULL) {
        std::fputs("[fail] portable AArch64 CRC32C mismatch\n", stderr);
        return 3;
    }

    std::puts("[ok] OHOS AArch64 portable fallback: 3/3 checks passed");
    return 0;
}
