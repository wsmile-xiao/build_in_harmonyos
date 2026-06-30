#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ident.h>

int main(void) {
    int failures = 0;

    /* Test 1: id_version string */
    if (id_version && strcmp(id_version, "0.32") == 0) {
        printf("PASS: id_version = \"%s\"\n", id_version);
    } else {
        printf("FAIL: id_version = \"%s\" (expected \"0.32\")\n",
               id_version ? id_version : "(null)");
        failures++;
    }

    /* Test 2: IDBUFSIZE macro */
    if (IDBUFSIZE == 2048) {
        printf("PASS: IDBUFSIZE = %d\n", IDBUFSIZE);
    } else {
        printf("FAIL: IDBUFSIZE = %d (expected 2048)\n", IDBUFSIZE);
        failures++;
    }

    /* Test 3: IPPORT_IDENT macro */
    if (IPPORT_IDENT == 113) {
        printf("PASS: IPPORT_IDENT = %d\n", IPPORT_IDENT);
    } else {
        printf("FAIL: IPPORT_IDENT = %d (expected 113)\n", IPPORT_IDENT);
        failures++;
    }

    /* Test 4: sizeof(ident_t) — fd (int=4) + buf[IDBUFSIZE=2048] */
    if (sizeof(ident_t) == sizeof(int) + IDBUFSIZE) {
        printf("PASS: sizeof(ident_t) = %zu (= int + IDBUFSIZE)\n", sizeof(ident_t));
    } else {
        printf("FAIL: sizeof(ident_t) = %zu (expected %zu)\n",
               sizeof(ident_t), sizeof(int) + IDBUFSIZE);
        failures++;
    }

    /* Test 5: sizeof(IDENT) — 2 ints + 3 pointers */
    if (sizeof(IDENT) == 2 * sizeof(int) + 3 * sizeof(char *)) {
        printf("PASS: sizeof(IDENT) = %zu (= 2*int + 3*ptr)\n", sizeof(IDENT));
    } else {
        printf("FAIL: sizeof(IDENT) = %zu (expected %zu)\n",
               sizeof(IDENT), 2 * sizeof(int) + 3 * sizeof(char *));
        failures++;
    }

    /* Test 6: id_fileno macro */
    ident_t id;
    id.fd = 42;
    if (id_fileno(&id) == 42) {
        printf("PASS: id_fileno macro works\n");
    } else {
        printf("FAIL: id_fileno returned %d (expected 42)\n", id_fileno(&id));
        failures++;
    }

    if (failures == 0) {
        printf("\nAll tests passed.\n");
        return 0;
    } else {
        printf("\n%d test(s) failed.\n", failures);
        return 1;
    }
}
