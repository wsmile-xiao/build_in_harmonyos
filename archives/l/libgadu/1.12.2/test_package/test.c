#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <libgadu.h>

/* R34: consumer test must call the real library API (offline, no network).
 * 4 real assertions:
 *  1. gg_libgadu_version() reports 1.12.2
 *  2. gg_fix32 double-swap round-trips
 *  3. gg_fix16 double-swap round-trips
 *  4. gg_crc32 is deterministic and input-sensitive
 */
int main(void)
{
    int failures = 0;

    /* 1. version */
    const char *ver = gg_libgadu_version();
    if (ver == NULL || strcmp(ver, "1.12.2") != 0) {
        printf("FAIL: gg_libgadu_version() = \"%s\", want \"1.12.2\"\n",
               ver ? ver : "(null)");
        failures++;
    } else {
        printf("PASS: gg_libgadu_version() = \"%s\"\n", ver);
    }

    /* 2. fix32 round-trip */
    {
        uint32_t v = 0x12345678u;
        uint32_t r = gg_fix32(gg_fix32(v));
        if (r != v) {
            printf("FAIL: gg_fix32 round-trip 0x%08x -> 0x%08x\n", v, r);
            failures++;
        } else {
            printf("PASS: gg_fix32 round-trip 0x%08x\n", v);
        }
    }

    /* 3. fix16 round-trip */
    {
        uint16_t v = 0x1234u;
        uint16_t r = gg_fix16(gg_fix16(v));
        if (r != v) {
            printf("FAIL: gg_fix16 round-trip 0x%04x -> 0x%04x\n", v, r);
            failures++;
        } else {
            printf("PASS: gg_fix16 round-trip 0x%04x\n", v);
        }
    }

    /* 4. crc32 determinism + sensitivity */
    {
        uint32_t c1 = gg_crc32(0, (const unsigned char *)"test", 4);
        uint32_t c2 = gg_crc32(0, (const unsigned char *)"test", 4);
        uint32_t c3 = gg_crc32(0, (const unsigned char *)"Test", 4);
        if (c1 != c2 || c1 == 0 || c1 == c3) {
            printf("FAIL: gg_crc32 determinism c1=0x%08x c2=0x%08x c3=0x%08x\n",
                   c1, c2, c3);
            failures++;
        } else {
            printf("PASS: gg_crc32 deterministic c1=0x%08x c3=0x%08x\n", c1, c3);
        }
    }

    if (failures > 0) {
        printf("RESULT: %d/4 FAILED\n", failures);
        return 1;
    }
    printf("RESULT: 4/4 passed\n");
    return 0;
}
