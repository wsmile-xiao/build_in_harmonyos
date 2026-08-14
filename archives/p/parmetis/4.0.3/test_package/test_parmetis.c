/* test_parmetis.c — ParMETIS L1 test (R34: must call ParMETIS API)
 *
 * Partitions a simple 4-vertex ring graph into 2 parts using
 * ParMETIS_V3_PartKway. Runs in MPI singleton mode (no mpirun).
 *
 * Graph topology (ring): 0-1-2-3-0
 * Expected: 2 vertices per partition, edgecut >= 2
 */
#include <mpi.h>
#include <parmetis.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    int rank, size;

    if (MPI_Init(&argc, &argv) != MPI_SUCCESS) {
        fprintf(stderr, "MPI_Init failed\n");
        return 1;
    }
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (size != 1) {
        fprintf(stderr, "Expected singleton mode (size=1), got size=%d\n", size);
        MPI_Finalize();
        return 1;
    }

    /* 4-vertex ring graph: 0-1, 1-2, 2-3, 3-0 */
    idx_t nvtxs = 4;
    idx_t vtxdist[] = {0, 4};        /* single process owns all vertices */
    idx_t xadj[] = {0, 2, 4, 6, 8};  /* CSR offsets */
    idx_t adjncy[] = {1, 3, 0, 2, 1, 3, 0, 2};
    idx_t ncon = 1;
    idx_t nparts = 2;
    idx_t edgecut = -1;
    idx_t part[4] = {0, 0, 0, 0};
    real_t tpwgts[] = {0.5, 0.5};
    real_t ubvec[] = {1.05};
    idx_t options[] = {0};
    idx_t wgtflag = 0;
    idx_t numflag = 0;
    MPI_Comm comm = MPI_COMM_WORLD;

    int result = ParMETIS_V3_PartKway(
        vtxdist, xadj, adjncy, NULL, NULL,
        &wgtflag, &numflag, &ncon, &nparts,
        tpwgts, ubvec, options, &edgecut, part, &comm);

    if (result != 1) {
        fprintf(stderr, "ParMETIS_V3_PartKway failed with code %d (expected METIS_OK=1)\n", result);
        MPI_Finalize();
        return 1;
    }

    if (edgecut < 0) {
        fprintf(stderr, "Invalid edgecut value: %d\n", (int)edgecut);
        MPI_Finalize();
        return 1;
    }

    printf("ParMETIS partition OK: edgecut=%d, parts=[%d,%d,%d,%d]\n",
           (int)edgecut, (int)part[0], (int)part[1], (int)part[2], (int)part[3]);
    printf("test parmetis 4.0.3: PASS\n");
    MPI_Finalize();
    return 0;
}
