#include <cstdio>
#include <cstring>
#include "MurmurHash3.h"

int main(void) {
    /* Known test vector: MurmurHash3_x86_32("", seed=0) == 0 */
    uint32_t empty_hash = 0;
    MurmurHash3_x86_32("", 0, 0, &empty_hash);
    if (empty_hash != 0) {
        printf("FAIL: MurmurHash3_x86_32(\"\", 0) = 0x%08x, expected 0\n", empty_hash);
        return 1;
    }

    /* Known test vector: MurmurHash3_x86_32("hello", seed=0) == 0x248bfa47 */
    const char *hello = "hello";
    uint32_t hello_hash = 0;
    MurmurHash3_x86_32(hello, (int)strlen(hello), 0, &hello_hash);
    if (hello_hash != 0x248bfa47) {
        printf("FAIL: MurmurHash3_x86_32(\"hello\", 0) = 0x%08x, expected 0x248bfa47\n", hello_hash);
        return 1;
    }

    /* Determinism check */
    uint32_t hello_hash2 = 0;
    MurmurHash3_x86_32(hello, (int)strlen(hello), 0, &hello_hash2);
    if (hello_hash != hello_hash2) {
        printf("FAIL: hash not deterministic\n");
        return 1;
    }

    /* x64_128 smoke test */
    uint64_t out128[2];
    MurmurHash3_x64_128(hello, (int)strlen(hello), 0, out128);
    printf("MurmurHash3_x64_128(\"hello\", 0) = 0x%016llx 0x%016llx\n",
           (unsigned long long)out128[0], (unsigned long long)out128[1]);

    printf("All MurmurHash3 tests passed!\n");
    return 0;
}
