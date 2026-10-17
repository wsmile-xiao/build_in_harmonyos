// SPDX-License-Identifier: Apache-2.0
// Deterministic consumer checks for the packaged KleidiAI public API.

#include <cstdint>
#include <cstdio>
#include <cstdlib>

#include "kai/kai_common.h"

static int checks = 0;

static void check(bool ok, const char* message) {
    if (!ok) {
        std::fprintf(stderr, "FAIL: %s\n", message);
        std::exit(1);
    }
    ++checks;
}

int main() {
    // 1. Version string is non-empty and carries a digit.
    const char* version = kai_get_version();
    check(version != nullptr && version[0] != '\0', "kai_get_version returns non-empty");
    bool has_digit = false;
    for (const char* p = version; *p != '\0'; ++p) {
        has_digit = has_digit || (*p >= '0' && *p <= '9');
    }
    check(has_digit, "version string contains a digit");

    // 2. Datatype byte sizes derived from the public enum encoding.
    check(kai_get_datatype_size_in_bytes(kai_dt_f32) == 4, "f32 size is 4");
    check(kai_get_datatype_size_in_bytes(kai_dt_f16) == 2, "f16 size is 2");
    check(kai_get_datatype_size_in_bytes(kai_dt_int8) == 1, "int8 size is 1");

    // 3. bf16<->f32 conversion round-trips for an exactly representable value.
    check(kai_cast_f32_bf16(kai_cast_bf16_f32(2.0F)) == 2.0F, "bf16 round-trip");

    // 4. Round-up helper semantics.
    check(kai_roundup(5, 4) == 8, "roundup(5,4) == 8");
    check(kai_roundup(8, 4) == 8, "roundup(8,4) == 8");
    check(kai_roundup(0, 4) == 0, "roundup(0,4) == 0");

    // 5. SVE vector length comes from the linked static library (non-inline
    //    symbol implemented in kai_common_sve_asm.S).
    const uint64_t sve_vl = kai_get_sve_vector_length_u8();
    check(sve_vl > 0, "SVE vector length is non-zero");

    std::printf("kleidiai consumer test passed (%d assertions)\n", checks);
    return 0;
}
