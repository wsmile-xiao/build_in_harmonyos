#include <igraph.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* Zero-initialize so the cleanup path is safe if igraph_small()
     * returns nonzero before writing g — igraph_destroy() on an
     * all-zero igraph_t is a no-op (internal pointers are NULL). */
    igraph_t g = {0};
    int ret;
    int rc = 0; /* 0 = PASS, 1 = FAIL */

    /* Test 1: Create a simple graph with 3 vertices and 3 edges.
     * igraph_small() takes a varargs edge list directly (vertex ID
     * pairs terminated by -1); no vector wrapper is needed. */
    ret = igraph_small(&g, 0, IGRAPH_UNDIRECTED, 0, 1, 1, 2, 2, 0, -1);
    if (ret != 0) {
        fprintf(stderr, "FAIL: igraph_small returned %d\n", ret);
        rc = 1;
        goto cleanup;
    }
    printf("PASS: igraph_small created graph\n");

    /* Test 2: Verify graph has 3 vertices */
    igraph_integer_t n = igraph_vcount(&g);
    if (n != 3) {
        fprintf(stderr, "FAIL: expected 3 vertices, got %d\n", (int)n);
        rc = 1;
        goto cleanup;
    }
    printf("PASS: graph has %d vertices\n", (int)n);

    /* Test 3: Verify graph has 3 edges */
    igraph_integer_t e = igraph_ecount(&g);
    if (e != 3) {
        fprintf(stderr, "FAIL: expected 3 edges, got %d\n", (int)e);
        rc = 1;
        goto cleanup;
    }
    printf("PASS: graph has %d edges\n", (int)e);

    printf("igraph 1.0.0: all tests PASSED\n");
cleanup:
    igraph_destroy(&g);
    return rc;
}
