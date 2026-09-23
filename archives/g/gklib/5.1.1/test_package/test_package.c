#include <GKlib.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    int failures = 0;
    int *values = (int *)gk_malloc(4 * sizeof(int), "consumer values");
    char *copy = gk_strdup("  gklib  ");
    gk_ikv_t pairs[3] = {{3, 30}, {1, 10}, {2, 20}};

    values[0] = 4;
    values[1] = 8;
    values[2] = 15;
    values[3] = 16;
    if (values[0] != 4 || values[3] != 16) {
        ++failures;
    }

    if (strcmp(gk_strhprune(copy, " "), "gklib  ") != 0) {
        ++failures;
    }
    if (strcmp(gk_strtprune(copy, " "), "gklib") != 0) {
        ++failures;
    }

    gk_ikvsorti(3, pairs);
    if (pairs[0].key != 1 || pairs[1].key != 2 || pairs[2].key != 3) {
        ++failures;
    }
    if (pairs[0].val != 10 || pairs[2].val != 30) {
        ++failures;
    }

    if (gk_log2(1) != 0 || gk_log2(16) != 4) {
        ++failures;
    }

    gk_free((void **)&values, (void **)&copy, LTERM);
    if (values != NULL || copy != NULL) {
        ++failures;
    }

    if (failures == 0) {
        printf("gklib 5.1.1 consumer: 7 assertions passed\n");
    }
    return failures == 0 ? 0 : 1;
}
