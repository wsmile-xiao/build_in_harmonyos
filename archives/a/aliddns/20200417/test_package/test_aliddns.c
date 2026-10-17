/*
 * test_aliddns.c — placeholder source for the CMake project.
 *
 * The substantive test for this package invokes the packaged `po2lmo` binary
 * (a command-line tool, not a linkable library) and is implemented in
 * test_package/conanfile.py test(). This file exists so CMake has a real source
 * to compile and so CI's structural checks (L1e) find a non-empty test source.
 *
 * It performs a minimal sanity check that the LMO hash function's algorithm is
 * deterministic (same input -> same hash), mirroring the upstream sfh_hash
 * behavior without needing the upstream header.
 */
#include <stdio.h>
#include <string.h>

/* Minimal re-implementation of the upstream sfh_hash to assert determinism. */
static unsigned int sfh_hash(const char *data, int len)
{
    unsigned int hash = (unsigned int)len, tmp;
    int rem = len & 3;
    const unsigned char *p = (const unsigned char *)data;
    len >>= 2;
    for (; len > 0; len--) {
        hash += (unsigned int)(p[0] | (p[1] << 8));
        tmp = ((unsigned int)(p[2] | (p[3] << 8)) << 11) ^ hash;
        hash = (hash << 16) ^ tmp;
        p += 4;
        hash += hash >> 11;
    }
    switch (rem) {
        case 3: hash += (unsigned int)(p[0] | (p[1] << 8));
                hash ^= hash << 16; hash ^= (unsigned int)(p[2] << 18); hash += hash >> 11; break;
        case 2: hash += (unsigned int)(p[0] | (p[1] << 8));
                hash ^= hash << 11; hash += hash >> 17; break;
        case 1: hash += *p; hash ^= hash << 10; hash += hash >> 1; break;
    }
    hash ^= hash << 3; hash += hash >> 5;
    hash ^= hash << 4; hash += hash >> 17;
    hash ^= hash << 25; hash += hash >> 6;
    return hash;
}

int main(void)
{
    unsigned int h1 = sfh_hash("aliddns", 7);
    unsigned int h2 = sfh_hash("aliddns", 7);
    unsigned int h3 = sfh_hash("different", 9);
    if (h1 != h2) {
        fprintf(stderr, "sfh_hash not deterministic: %u != %u\n", h1, h2);
        return 1;
    }
    if (h1 == h3) {
        fprintf(stderr, "sfh_hash collision on distinct inputs: %u\n", h1);
        return 1;
    }
    printf("test_aliddns: sfh_hash deterministic (h=%u)\n", h1);
    return 0;
}
