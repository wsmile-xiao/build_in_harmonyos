/* test.c — metis L1 test (R34: must call metis API)
 *
 * Calls METIS_PartGraphRecursive to partition a simple 4-vertex graph.
 * This is a real functional test of the metis library API.
 */
#include <stdio.h>
#include <stdlib.h>
#include "metis.h"

int main(void) {
    /* Simple graph: 4 vertices, edges (0-1), (1-2), (2-3), (0-3)
     * adjacency: vertex 0 -> {1,3}, vertex 1 -> {0,2}, vertex 2 -> {1,3}, vertex 3 -> {0,2} */
    idx_t nvtxs = 4;
    idx_t ncon = 1;
    idx_t xadj[] = {0, 2, 4, 6, 8};
    idx_t adjncy[] = {1, 3, 0, 2, 1, 3, 0, 2};
    idx_t nparts = 2;
    idx_t objval = 0;
    idx_t part[] = {0, 0, 0, 0};

    /* Call metis API: METIS_PartGraphRecursive */
    int ret = METIS_PartGraphRecursive(
        &nvtxs,     /* number of vertices */
        &ncon,      /* number of constraints */
        xadj,       /* adjacency structure */
        adjncy,     /* adjacency structure */
        NULL,       /* vwgt */
        NULL,       /* vsize */
        NULL,       /* adjwgt */
        &nparts,    /* number of partitions */
        NULL,       /* tpwgts */
        NULL,       /* ubvec */
        NULL,       /* options */
        &objval,    /* objective value output */
        part        /* partition vector output */
    );

    if (ret != METIS_OK) {
        fprintf(stderr, "METIS_PartGraphRecursive failed with code %d\n", ret);
        return 1;
    }

    printf("METIS partition succeeded: objval=%d, parts=[%d,%d,%d,%d]\n",
           (int)objval, (int)part[0], (int)part[1], (int)part[2], (int)part[3]);
    printf("test metis 5.1.0: OK\n");
    return 0;
}
