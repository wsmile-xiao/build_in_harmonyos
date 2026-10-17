#include <stdio.h>
#include <stdlib.h>
#include <cloog/cloog.h>

int main(void) {
    /* Verify cloog library is functional: create a state and check version */
    CloogState *state = cloog_state_malloc();
    if (!state) {
        fprintf(stderr, "cloog_state_malloc failed\n");
        return 1;
    }

    /* Check that we can access the cloog version */
    const char *ver = cloog_version();
    if (!ver || ver[0] == '\0') {
        fprintf(stderr, "cloog_version returned empty\n");
        cloog_state_free(state);
        return 1;
    }

    printf("cloog version: %s\n", ver);
    printf("test cloog 0.21.1: OK\n");

    cloog_state_free(state);
    return 0;
}
