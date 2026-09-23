#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Include the library header */
#include <cap-ng.h>

int main(void) {
    /* Test 1: clear and verify state */
    capng_clear(CAPNG_SELECT_BOTH);
    int rc = capng_have_capabilities(CAPNG_SELECT_BOTH);
    if (rc != CAPNG_NONE) {
        /* On some platforms the process has capabilities; try get_caps_process first */
        capng_get_caps_process();
        capng_clear(CAPNG_SELECT_BOTH);
        rc = capng_have_capabilities(CAPNG_SELECT_BOTH);
    }
    if (rc != CAPNG_NONE) {
        printf("FAIL: clear did not result in CAPNG_NONE (got %d)\n", rc);
        return 1;
    }
    printf("PASS: capng_clear works\n");

    /* Test 2: fill and verify */
    capng_fill(CAPNG_SELECT_BOTH);
    rc = capng_have_capabilities(CAPNG_SELECT_BOTH);
    if (rc != CAPNG_FULL) {
        printf("FAIL: fill did not result in CAPNG_FULL (got %d)\n", rc);
        return 1;
    }
    printf("PASS: capng_fill works\n");

    /* Test 3: update a specific capability */
    capng_clear(CAPNG_SELECT_BOTH);
    rc = capng_update(CAPNG_ADD, CAPNG_EFFECTIVE, CAP_CHOWN);
    if (rc != 0) {
        printf("FAIL: capng_update returned %d\n", rc);
        return 1;
    }
    rc = capng_have_capability(CAPNG_EFFECTIVE, CAP_CHOWN);
    if (!rc) {
        printf("FAIL: capng_have_capability returned 0 for CAP_CHOWN\n");
        return 1;
    }
    printf("PASS: capng_update + capng_have_capability work\n");

    /* Test 4: text conversion */
    char *text = capng_print_caps_text(CAPNG_PRINT_BUFFER, CAPNG_EFFECTIVE);
    if (text == NULL) {
        printf("FAIL: capng_print_caps_text returned NULL\n");
        return 1;
    }
    const char *name = capng_capability_to_name(CAP_CHOWN);
    if (name == NULL) {
        printf("FAIL: capng_capability_to_name returned NULL\n");
        free(text);
        return 1;
    }
    if (strcmp(text, name) != 0) {
        printf("FAIL: text mismatch: %s != %s\n", text, name);
        free(text);
        return 1;
    }
    printf("PASS: text conversion works (%s)\n", text);
    free(text);

    /* Test 5: save/restore state */
    void *saved = capng_save_state();
    if (saved == NULL) {
        printf("FAIL: capng_save_state returned NULL\n");
        return 1;
    }
    capng_clear(CAPNG_SELECT_BOTH);
    capng_restore_state(&saved);
    rc = capng_have_capability(CAPNG_EFFECTIVE, CAP_CHOWN);
    if (!rc) {
        printf("FAIL: restore did not restore CAP_CHOWN\n");
        return 1;
    }
    printf("PASS: save/restore state works\n");

    /* Test 6: updatev (multiple capabilities at once) */
    capng_clear(CAPNG_SELECT_BOTH);
    rc = capng_updatev(CAPNG_ADD, CAPNG_EFFECTIVE,
                       CAP_CHOWN, CAP_FOWNER, CAP_KILL, -1);
    if (rc != 0) {
        printf("FAIL: capng_updatev returned %d\n", rc);
        return 1;
    }
    if (!capng_have_capability(CAPNG_EFFECTIVE, CAP_CHOWN) ||
        !capng_have_capability(CAPNG_EFFECTIVE, CAP_FOWNER) ||
        !capng_have_capability(CAPNG_EFFECTIVE, CAP_KILL)) {
        printf("FAIL: updatev capabilities not set\n");
        return 1;
    }
    printf("PASS: capng_updatev works\n");

    printf("\nAll tests passed!\n");
    return 0;
}
