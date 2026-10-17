#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "levenshtein.h"

int main(void) {
    /* 真实调用公开 API，验证第三方消费者可编译、链接并正确运行 */
    const char *a = "sitting";
    const char *b = "kitten";
    size_t d = levenshtein(a, b);
    size_t dn = levenshtein_n(a, strlen(a), b, strlen(b));

    if (d != 3 || dn != 3) {
        fprintf(stderr, "FAIL: levenshtein(\"sitting\",\"kitten\")=%zu (exp 3), n-version=%zu\n", d, dn);
        return EXIT_FAILURE;
    }
    if (levenshtein("", "a") != 1 || levenshtein("", "") != 0) {
        fprintf(stderr, "FAIL: degenerate cases\n");
        return EXIT_FAILURE;
    }
    printf("levenshtein.c consumer test PASSED: distance(sitting,kitten)=%zu\n", d);
    return EXIT_SUCCESS;
}
