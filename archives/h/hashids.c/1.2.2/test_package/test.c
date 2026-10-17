/* test_package consumer test for hashids.c 1.2.2.
 * R34: must call the installed public API and verify observable results
 * (not a print-only stub).  Uses only public headers (<hashids.h>) and the
 * installed library.
 */
#include <stdio.h>
#include <string.h>
#include <hashids.h>

int
main(void)
{
    hashids_t *hashids = hashids_init(NULL); /* empty salt (upstream default) */
    if (hashids == NULL) {
        printf("FAIL: hashids_init\n");
        return 1;
    }

    char hash[128];
    unsigned long long nums[5] = {1ull, 2ull, 3ull, 4ull, 5ull};

    /* encode [1..5]: upstream documented example -> "ADf9h9i0sQ" */
    size_t n = hashids_encode(hashids, hash, 5, nums);
    if (n == 0) {
        printf("FAIL: hashids_encode\n");
        return 2;
    }
    hash[n] = '\0';
    if (strcmp(hash, "ADf9h9i0sQ") != 0) {
        printf("FAIL: encode got %s\n", hash);
        return 3;
    }

    /* roundtrip decode: [1..5] */
    unsigned long long out[8];
    size_t r = hashids_decode(hashids, hash, out, 8);
    if (r != 5 || out[0] != 1ull || out[1] != 2ull || out[2] != 3ull ||
        out[3] != 4ull || out[4] != 5ull) {
        printf("FAIL: decode roundtrip r=%zu\n", r);
        return 4;
    }

    /* encode_one: 12345 -> "j0gW" (upstream documented) */
    char one[32];
    size_t o = hashids_encode_one(hashids, one, 12345ull);
    if (o == 0) {
        printf("FAIL: hashids_encode_one\n");
        return 5;
    }
    one[o] = '\0';
    if (strcmp(one, "j0gW") != 0) {
        printf("FAIL: encode_one got %s\n", one);
        return 6;
    }

    /* encode_hex: "C0FFEE" -> "k7AVov" (upstream documented) */
    char hexbuf[32];
    size_t hx = hashids_encode_hex(hashids, hexbuf, "C0FFEE");
    if (hx == 0) {
        printf("FAIL: hashids_encode_hex\n");
        return 7;
    }
    hexbuf[hx] = '\0';
    if (strcmp(hexbuf, "k7AVov") != 0) {
        printf("FAIL: encode_hex got %s\n", hexbuf);
        return 8;
    }

    hashids_free(hashids);
    printf("hashids.c consumer OK: encode=%s decode_roundtrip=%zu hex=%s\n",
        hash, r, hexbuf);
    return 0;
}
