#include <stdio.h>
#include <stdlib.h>
#include <Judy.h>

int main(void) {
    int rc_int;
    Pvoid_t judy1_array = NULL;
    Pvoid_t judyL_array = NULL;
    PPvoid_t ppvalue;

    /* Test Judy1: bitmap array */
    J1S(rc_int, judy1_array, 100);
    if (rc_int != 1) {
        fprintf(stderr, "FAIL: J1S set returned %d\n", rc_int);
        return 1;
    }
    J1T(rc_int, judy1_array, 100);
    if (rc_int != 1) {
        fprintf(stderr, "FAIL: J1T test returned %d\n", rc_int);
        return 1;
    }
    J1T(rc_int, judy1_array, 200);
    if (rc_int != 0) {
        fprintf(stderr, "FAIL: J1T absent returned %d\n", rc_int);
        return 1;
    }

    /* Test JudyL: linear array */
    JLI(ppvalue, judyL_array, 42);
    if (ppvalue == NULL || ppvalue == (PPvoid_t)PJERR) {
        fprintf(stderr, "FAIL: JLI insert failed\n");
        return 1;
    }
    *((Word_t *)ppvalue) = 999;

    JLG(ppvalue, judyL_array, 42);
    if (ppvalue == NULL || ppvalue == (PPvoid_t)PJERR) {
        fprintf(stderr, "FAIL: JLG retrieve failed (key not found or memory error)\n");
        return 1;
    }
    if (*((Word_t *)ppvalue) != 999) {
        fprintf(stderr, "FAIL: JLG retrieve returned wrong value\n");
        return 1;
    }

    /* Cleanup */
    Word_t bytes_freed;
    J1FA(bytes_freed, judy1_array);
    JLFA(bytes_freed, judyL_array);

    printf("test judy 1.0.5: OK\n");
    return 0;
}
