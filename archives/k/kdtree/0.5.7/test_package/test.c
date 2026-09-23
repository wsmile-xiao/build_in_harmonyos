/* test_package consumer test for kdtree: exercise the public API
 * (kd_create / kd_insert3 / kd_nearest3) and verify an observable result.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "kdtree.h"

int main(void) {
    struct kdtree *kd = kd_create(3);
    if (!kd) {
        fprintf(stderr, "kd_create failed\n");
        return 1;
    }
    kd_insert3(kd, 1.0, 2.0, 3.0, (void *)"p1");
    kd_insert3(kd, 4.0, 5.0, 6.0, (void *)"p2");
    kd_insert3(kd, 1.1, 2.1, 3.1, (void *)"p3");

    struct kdres *res = kd_nearest3(kd, 1.0, 2.0, 3.0);
    if (kd_res_size(res) != 1) {
        fprintf(stderr, "expected 1 nearest result, got %d\n", kd_res_size(res));
        return 1;
    }
    const void *data = kd_res_item(res, NULL);
    if (data == NULL || strcmp((const char *)data, "p1") != 0) {
        fprintf(stderr, "nearest query returned unexpected data\n");
        return 1;
    }
    kd_res_free(res);
    kd_free(kd);
    printf("kdtree consumer test PASSED\n");
    return 0;
}
