#include <stdio.h>
#include <tommath.h>

int main(void)
{
    mp_int a, b, sum, product;
    mp_err err;

    err = mp_init_multi(&a, &b, &sum, &product, NULL);
    if (err != MP_OKAY) {
        return 1;
    }

    mp_set_u32(&a, 12345u);
    mp_set_u32(&b, 67890u);

    err = mp_add(&a, &b, &sum);
    if (err != MP_OKAY || mp_get_u32(&sum) != 80235u) {
        mp_clear_multi(&a, &b, &sum, &product, NULL);
        return 2;
    }

    err = mp_mul(&a, &b, &product);
    if (err != MP_OKAY || mp_get_u64(&product) != 838102050u) {
        mp_clear_multi(&a, &b, &sum, &product, NULL);
        return 3;
    }

    mp_clear_multi(&a, &b, &sum, &product, NULL);
    puts("libtommath arithmetic tests passed");
    return 0;
}
