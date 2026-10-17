/* Consumer test for the installed upb package.
 *
 * Upstream has no stable public header for the low-level helpers, but the
 * installed tree ships upb/pb/varint.int.h, which is the API the upstream
 * test_varint exercises.  This consumer checks the same varint/zigzag
 * round-trips through the packaged headers + libupb.a. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "upb/pb/varint.int.h"

static int checks = 0;
static int fails = 0;

#define CHECK(cond, msg) do { \
    checks++; \
    if (!(cond)) { fails++; printf("FAIL: %s\n", (msg)); } \
} while (0)

int main(void)
{
    char buf[UPB_PB_VARINT_MAX_LEN];
    upb_decoderet r;
    size_t n;

    /* one byte */
    n = upb_vencode64(1, buf);
    CHECK(n == 1 && buf[0] == 1, "vencode64(1) is one byte 0x01");

    /* multi byte */
    n = upb_vencode64(300, buf);
    CHECK(n == 2, "vencode64(300) is two bytes");
    r = upb_vdecode_check2_branch64(buf);
    CHECK(r.val == 300, "vdecode(branch64) round-trips 300");
    CHECK(r.p == buf + n, "vdecode consumed exactly the encoded length");

    /* 32-bit fast path */
    {
        uint64_t enc = upb_vencode32((uint32_t)0xa01);
        char b2[16];
        memset(b2, 0, sizeof(b2));
        memcpy(b2, &enc, 8);
        r = upb_vdecode_check2_branch64(b2);
        CHECK(r.val == 0xa01, "vencode32/vdecode round-trips 0xa01");
    }

    /* a value needing the 10-byte encoding */
    n = upb_vencode64(UINT64_MAX, buf);
    CHECK(n == 10, "vencode64(UINT64_MAX) is ten bytes");
    r = upb_vdecode_check2_branch64(buf);
    CHECK(r.val == UINT64_MAX, "vdecode round-trips UINT64_MAX");

    /* zigzag */
    CHECK(upb_zzdec_32(upb_zzenc_32(12345)) == 12345, "zigzag32 round-trips");
    CHECK(upb_zzdec_64(upb_zzenc_64(-42)) == -42, "zigzag64 round-trips -42");
    CHECK(upb_zzdec_64(upb_zzenc_64(1234567890123LL)) == 1234567890123LL,
          "zigzag64 round-trips a large positive value");

    /* encoded size helper */
    CHECK(upb_value_size(300) == 2 && upb_value_size(0) == 1,
          "upb_value_size matches the encoding length");

    printf("UPB_CHECK_SUMMARY checks=%d fails=%d\n", checks, fails);
    return fails == 0 ? 0 : 1;
}
