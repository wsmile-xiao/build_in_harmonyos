#include <stdio.h>
#include "SpiceUsr.h"

int main(void) {
    /* Test that we can link against cspice and call a function */
    SpiceDouble pi_val = pi_c();
    printf("cspice pi() = %.15f\n", pi_val);
    printf("test cspice 67: OK\n");
    return 0;
}
