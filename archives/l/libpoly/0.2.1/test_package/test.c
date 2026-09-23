#include <poly/integer.h>
#include <stdio.h>

int main(void) {
    lp_integer_t a;
    lp_integer_t b;
    lp_integer_t s;
    lp_integer_construct_from_int(lp_Z, &a, 6);
    lp_integer_construct_from_int(lp_Z, &b, 7);
    lp_integer_construct(&s);
    lp_integer_add(lp_Z, &s, &a, &b);
    if (lp_integer_to_int(&s) != 13) {
        fprintf(stderr, "6+7 failed\n");
        return 1;
    }
    printf("libpoly version=0.2.1 6+7=13 ok\n");
    return 0;
}
