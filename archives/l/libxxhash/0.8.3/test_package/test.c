#include <stdio.h>
#include <string.h>
#include "xxhash.h"

int main(void) {
    /* Test XXH64 one-shot */
    const char *data = "Hello, HarmonyOS!";
    size_t len = strlen(data);
    XXH64_hash_t hash = XXH64(data, len, 0);
    if (hash == 0) {
        printf("FAIL: XXH64 returned 0 for non-empty input\n");
        return 1;
    }

    /* Test determinism: same input + seed => same hash */
    XXH64_hash_t hash2 = XXH64(data, len, 0);
    if (hash != hash2) {
        printf("FAIL: XXH64 non-deterministic\n");
        return 1;
    }

    /* Test streaming API */
    XXH64_state_t *state = XXH64_createState();
    if (state == NULL) {
        printf("FAIL: XXH64_createState returned NULL\n");
        return 1;
    }
    if (XXH64_reset(state, 42) != XXH_OK) {
        printf("FAIL: XXH64_reset failed\n");
        return 1;
    }
    if (XXH64_update(state, data, len) != XXH_OK) {
        printf("FAIL: XXH64_update failed\n");
        return 1;
    }
    XXH64_hash_t stream_hash = XXH64_digest(state);
    if (stream_hash == 0) {
        printf("FAIL: XXH64 streaming returned 0\n");
        return 1;
    }
    XXH64_freeState(state);

    /* Test XXH32 */
    XXH32_hash_t h32 = XXH32(data, len, 0);
    if (h32 == 0) {
        printf("FAIL: XXH32 returned 0 for non-empty input\n");
        return 1;
    }

    /* Test different seed produces different hash */
    XXH64_hash_t hash_seed1 = XXH64(data, len, 1);
    XXH64_hash_t hash_seed2 = XXH64(data, len, 2);
    if (hash_seed1 == hash_seed2) {
        printf("FAIL: different seeds produced same hash\n");
        return 1;
    }

    printf("All xxHash tests passed\n");
    return 0;
}
