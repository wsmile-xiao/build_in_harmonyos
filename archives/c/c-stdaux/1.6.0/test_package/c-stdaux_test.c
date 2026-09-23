#include <c-stdaux.h>

#include <stddef.h>
#include <stdio.h>

struct node {
    int id;
    char tag;
};

static int check(int condition, const char *message) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    printf("PASS: %s\n", message);
    return 0;
}

int main(void) {
    int failures = 0;

    /* c_assert always evaluates its argument and passes on true expressions. */
    c_assert(1 == 1);
    printf("PASS: c_assert accepts true expressions\n");

    /* C_ARRAY_SIZE reports the element count of a real array. */
    {
        int samples[7];
        failures += check(C_ARRAY_SIZE(samples) == 7,
                          "C_ARRAY_SIZE counts array elements");
    }

    /* c_memzero clears the whole buffer. */
    {
        unsigned char buffer[16];
        size_t i;
        int zeroed = 1;
        c_memzero(buffer, sizeof(buffer));
        for (i = 0; i < sizeof(buffer); ++i) {
            if (buffer[i] != 0) {
                zeroed = 0;
            }
        }
        failures += check(zeroed, "c_memzero clears the buffer");
    }

    /* c_memcpy/c_memcmp behave like their libc counterparts. */
    {
        unsigned char dst[4];
        c_memcpy(dst, "abcd", 4);
        failures += check(c_memcmp(dst, "abcd", 4) == 0,
                          "c_memcpy plus c_memcmp roundtrip");
    }

    /* Byte-order load helpers decode known patterns. */
    {
        static const unsigned char be[4] = { 0x12, 0x34, 0x56, 0x78 };
        static const unsigned char le[4] = { 0x78, 0x56, 0x34, 0x12 };
        failures += check(c_load_32be_unaligned(be, 0) == 0x12345678u,
                          "c_load_32be_unaligned decodes big endian");
        failures += check(c_load_32le_unaligned(le, 0) == 0x12345678u,
                          "c_load_32le_unaligned decodes little endian");
    }

    /* c_container_of recovers the enclosing object. */
    {
        struct node n;
        struct node *p;
        n.id = 42;
        n.tag = 'x';
        p = c_container_of(&n.id, struct node, id);
        failures += check(p == &n && p->tag == 'x',
                          "c_container_of recovers the container");
    }

    if (failures != 0) {
        fprintf(stderr, "c-stdaux 1.6.0 test failed\n");
        return 1;
    }

    printf("c-stdaux 1.6.0: all 7 checks passed\n");
    return 0;
}
