#include <stdio.h>
#include <string.h>

#include <nexstar.h>

#ifndef __aarch64__
#error "HarmonyOS PC package must target AArch64"
#endif

_Static_assert(sizeof(void *) == 8, "HarmonyOS PC requires a 64-bit ABI");

int main(void) {
    char encoded[32];
    double ra = 0.0;
    double de = 0.0;

    if (dd2nex(90.0, -30.0, encoded) != RC_OK) {
        return 1;
    }
    if (strcmp(encoded, "4000,EAAA") != 0) {
        fprintf(stderr, "Unexpected encoded coordinates: %s\n", encoded);
        return 2;
    }
    if (nex2dd(encoded, &ra, &de) != RC_OK) {
        return 3;
    }
    if (ra < 89.99 || ra > 90.01 || de < -30.01 || de > -29.99) {
        fprintf(stderr, "Unexpected decoded coordinates: %.6f, %.6f\n", ra, de);
        return 4;
    }
    puts("PASS: HarmonyOS AArch64 public API and ABI");
    return 0;
}
