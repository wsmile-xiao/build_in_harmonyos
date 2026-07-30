#include <stdio.h>
#include <stdlib.h>
#include "jitterentropy.h"

int main(void) {
    int ret;
    struct rand_data *ec = NULL;
    unsigned char buffer[32];

    /* Initialize jitterentropy */
    ret = jent_entropy_init();
    if (ret != 0) {
        fprintf(stderr, "ERROR: jent_entropy_init() failed with code %d\n", ret);
        return 1;
    }

    /* Allocate entropy collector */
    ec = jent_entropy_collector_alloc(0, 0);
    if (!ec) {
        fprintf(stderr, "ERROR: jent_entropy_collector_alloc() failed\n");
        return 1;
    }

    /* Read entropy */
    ssize_t nread = jent_read_entropy(ec, (char *)buffer, sizeof(buffer));
    if (nread != (ssize_t)sizeof(buffer)) {
        fprintf(stderr, "ERROR: jent_read_entropy() returned %zd\n", nread);
        jent_entropy_collector_free(ec);
        return 1;
    }

    /* Print first few bytes as hex to verify we got real data */
    printf("Entropy bytes:");
    for (int i = 0; i < 8 && i < nread; i++) {
        printf(" %02x", buffer[i]);
    }
    printf("\n");

    jent_entropy_collector_free(ec);
    printf("jitterentropy-library 3.6.3: ALL TESTS PASSED\n");
    return 0;
}
