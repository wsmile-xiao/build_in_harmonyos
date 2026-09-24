#include <stdio.h>
#include <stdlib.h>
#include "simint/simint.h"
#include "simint/shell/shell.h"

/* HarmonyOS consumer test: real calls to simint API
 * - simint_init / simint_finalize
 * - shell initialize / allocate / normalize
 * Covers s and p shells as in upstream example1
 */
int main(void) {
    printf("[simint] consumer test start\n");

    simint_init();
    printf("[simint] simint_init OK\n");

    struct simint_shell shells[2];
    simint_initialize_shell(&shells[0]);
    simint_initialize_shell(&shells[1]);

    simint_allocate_shell(3, &shells[0]);
    simint_allocate_shell(3, &shells[1]);

    // s shell (oxygen-like)
    shells[0].am = 0; shells[0].nprim = 3;
    shells[0].x = 0.0; shells[0].y = 0.0; shells[0].z = 0.0;
    shells[0].alpha[0] = 130.70932; shells[0].coef[0] = 0.15432897;
    shells[0].alpha[1] = 23.808861; shells[0].coef[1] = 0.53532814;
    shells[0].alpha[2] = 6.4436083; shells[0].coef[2] = 0.44463454;

    // p shell
    shells[1].am = 1; shells[1].nprim = 3;
    shells[1].x = 0.0; shells[1].y = 0.0; shells[1].z = 0.0;
    shells[1].alpha[0] = 5.0331513; shells[1].coef[0] = 0.15591627;
    shells[1].alpha[1] = 1.1695961; shells[1].coef[1] = 0.60768372;
    shells[1].alpha[2] = 0.3803890; shells[1].coef[2] = 0.39195739;

    simint_normalize_shells(2, shells);
    printf("[simint] simint_normalize_shells OK (s + p)\n");

    // Verify normalized shell still has expected AM
    if (shells[0].am != 0 || shells[1].am != 1) {
        fprintf(stderr, "[simint] shell AM mismatch\n");
        simint_free_shell(&shells[0]);
        simint_free_shell(&shells[1]);
        simint_finalize();
        return 1;
    }

    // Cleanup allocations
    simint_free_shell(&shells[0]);
    simint_free_shell(&shells[1]);
    printf("[simint] simint_free_shell OK\n");

    simint_finalize();
    printf("[simint] simint_finalize OK\n");
    printf("[simint] consumer test: OK\n");
    return 0;
}
