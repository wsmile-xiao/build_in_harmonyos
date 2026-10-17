/* Consumer test for libdecaf — exercises the public C API of the
 * Ed448-Goldilocks (decaf_448) implementation shipped by this package:
 * scalar arithmetic, point arithmetic, encode/decode round trip,
 * point validity and identity handling. */
#include <decaf.h>
#include <stdio.h>
#include <string.h>

#define CHECK(cond, msg)                                                      \
    do {                                                                      \
        if (!(cond)) {                                                        \
            printf("FAIL: %s\n", (msg));                                      \
            return 1;                                                         \
        }                                                                     \
        printf("ok: %s\n", (msg));                                            \
    } while (0)

int main(void) {
    decaf_448_scalar_t a, b, prod;
    decaf_448_point_t base, sum, dbl, dec, id;
    uint8_t ser1[DECAF_448_SER_BYTES], ser2[DECAF_448_SER_BYTES];

    /* Scalar arithmetic: 2 * 2 == 4 in the scalar field */
    decaf_448_scalar_set_unsigned(a, 2);
    decaf_448_scalar_set_unsigned(b, 4);
    decaf_448_scalar_mul(prod, a, a);
    CHECK(decaf_448_scalar_eq(prod, b), "scalar 2*2 == 4");

    /* Point arithmetic: 2*G == G + G */
    decaf_448_point_copy(base, decaf_448_point_base);
    decaf_448_point_add(sum, base, base);
    decaf_448_point_scalarmul(dbl, base, a);
    CHECK(decaf_448_point_eq(sum, dbl), "2*G == G+G");

    /* Encode / decode round trip */
    decaf_448_point_encode(ser1, sum);
    CHECK(decaf_448_point_decode(dec, ser1, DECAF_FALSE) == DECAF_SUCCESS,
          "encoded point decodes");
    decaf_448_point_encode(ser2, dec);
    CHECK(memcmp(ser1, ser2, DECAF_448_SER_BYTES) == 0,
          "encode/decode round trip");

    /* Base point is a valid group element */
    CHECK(decaf_448_point_valid(base) == DECAF_TRUE, "base point valid");

    /* Identity must be rejected when not explicitly allowed */
    decaf_448_point_copy(id, decaf_448_point_identity);
    decaf_448_point_encode(ser1, id);
    CHECK(decaf_448_point_decode(dec, ser1, DECAF_FALSE) != DECAF_SUCCESS,
          "identity rejected with allow_identity=FALSE");

    decaf_448_scalar_destroy(a);
    decaf_448_scalar_destroy(b);
    decaf_448_scalar_destroy(prod);
    decaf_448_point_destroy(base);
    decaf_448_point_destroy(sum);
    decaf_448_point_destroy(dbl);
    decaf_448_point_destroy(dec);
    decaf_448_point_destroy(id);

    printf("All libdecaf consumer tests passed.\n");
    return 0;
}
