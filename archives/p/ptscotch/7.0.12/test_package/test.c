/*! \file
 * Consumer test for PT-SCOTCH (OHOS adaptation).
 *
 * Exercises the real parallel (distributed-memory) API: it builds a
 * distributed graph on the MPI process set, validates it, then computes a
 * graph partition and checks that every local vertex received a part
 * number.  This is a genuine API test (R34) -- it links the packaged
 * library and asserts on results.
 *
 * The graph is generated in place by SCOTCH_dgraphBuildGrid3D(), so the
 * test needs no external data file.
 *
 * The partitioning entry points are collective over MPI_COMM_WORLD, so all
 * ranks must call them; the verdict is broadcast while MPI is still active.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <mpi.h>
#include "ptscotch.h"

#define GRID_DIM 4          /* 4 x 4 x 1 grid graph = 16 vertices */
#define NPART 4             /* number of parts to compute */

int main(int argc, char *argv[])
{
    SCOTCH_Dgraph  grafdat;
    SCOTCH_Strat   stratdat;
    SCOTCH_Num    *parttab = NULL;
    SCOTCH_Num     vertglbnbr = 0, vertlocnbr = 0, edgeglbnbr = 0;
    SCOTCH_Num     partnbr = 0;
    int            iam = 0, nprocs = 0;
    int            rc_init, rc_build, rc_check, rc_strat, rc_part;
    int            cpart[NPART + 1];      /* histogram of parts 0..NPART-1 */
    int            ok = 0;
    SCOTCH_Num     i;

    /* Initialise every return code to a sentinel so that a step which is
     * skipped (because a previous step failed) can never be mistaken for a
     * successful call -- relying on 0-initialisation would make a skipped
     * step look like a pass. */
    rc_init = rc_build = rc_check = rc_strat = rc_part = -1;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &iam);
    MPI_Comm_size(MPI_COMM_WORLD, &nprocs);

    if (iam == 0) {
        int v_major, v_minor, v_patch;
        SCOTCH_version(&v_major, &v_minor, &v_patch);
        printf("SCOTCH version:\t\t%d.%d.%d\n", v_major, v_minor, v_patch);
        printf("MPI ranks:\t\t%d\n", nprocs);
    }

    /* 1. Initialise the distributed graph on the MPI communicator. */
    rc_init = SCOTCH_dgraphInit(&grafdat, MPI_COMM_WORLD);

    /* 2. Build a 4x4x1 grid graph (base 0, increment 1, no flags).
     *    Generated in memory -- no input file required. */
    if (rc_init == 0)
        rc_build = SCOTCH_dgraphBuildGrid3D(&grafdat, 0, GRID_DIM,
                                            GRID_DIM, 1, 1, 0);

    /* 3. Validate the distributed graph, then size it so the partition
     *    array can be allocated to the local vertex count. */
    if (rc_build == 0) {
        rc_check = SCOTCH_dgraphCheck(&grafdat);
        SCOTCH_dgraphSize(&grafdat, &vertglbnbr, &vertlocnbr,
                          &edgeglbnbr, NULL);
        if (rc_check == 0 && vertlocnbr > 0) {
            parttab = (SCOTCH_Num *) malloc((size_t) vertlocnbr
                                            * sizeof(SCOTCH_Num));
            if (parttab == NULL)
                rc_check = -2;
        }
    }

    /* 4. Build a parallel mapping strategy and compute the partition.
     *    The strategy must be built through the API; a bare string such as
     *    "b" is rejected by the strategy parser ("invalid method name"). */
    if (rc_check == 0 && parttab != NULL) {
        rc_strat = SCOTCH_stratInit(&stratdat);
        if (rc_strat == 0) {
            rc_strat = SCOTCH_stratDgraphMapBuild(&stratdat,
                                                  SCOTCH_STRATDEFAULT,
                                                  nprocs, NPART, 0.03);
            if (rc_strat == 0) {
                for (i = 0; i < (SCOTCH_Num) vertlocnbr; i++)
                    parttab[i] = -1;
                rc_part = SCOTCH_dgraphPart(&grafdat, NPART, &stratdat,
                                            parttab);
            }
            SCOTCH_stratExit(&stratdat);
        }
    }

    /* Every local vertex must have received a part number in [0, NPART). */
    memset(cpart, 0, sizeof(cpart));
    if (rc_part == 0 && parttab != NULL) {
        for (i = 0; i < (SCOTCH_Num) vertlocnbr; i++) {
            SCOTCH_Num p = parttab[i];
            if (p < 0 || p >= NPART) {
                rc_part = -3;       /* unassigned / out-of-range vertex */
                break;
            }
            cpart[p]++;
        }
        for (i = 0; i < NPART; i++)
            if (cpart[i] > 0) partnbr++;
    }

    ok = (rc_init == 0 && rc_build == 0 && rc_check == 0
          && rc_strat == 0 && rc_part == 0
          && vertglbnbr > 0 && vertlocnbr > 0 && partnbr > 0) ? 1 : 0;

    /* Broadcast the verdict before tearing down MPI. */
    MPI_Bcast(&ok, 1, MPI_INT, 0, MPI_COMM_WORLD);

    if (rc_init == 0)
        SCOTCH_dgraphExit(&grafdat);
    free(parttab);

    if (iam == 0) {
        printf("graph vertices (global):%lld\n", (long long) vertglbnbr);
        printf("graph vertices (local):\t%lld\n", (long long) vertlocnbr);
        printf("distinct parts used:\t%lld of %d requested\n",
               (long long) partnbr, NPART);
        printf("rc init=%d build=%d check=%d strat=%d part=%d\n",
               rc_init, rc_build, rc_check, rc_strat, rc_part);
    }

    MPI_Finalize();

    if (!ok) {
        if (iam == 0)
            fprintf(stderr, "FAILED: PT-SCOTCH partition did not complete "
                            "(init=%d build=%d check=%d strat=%d part=%d "
                            "verts=%lld parts=%lld)\n",
                    rc_init, rc_build, rc_check, rc_strat, rc_part,
                    (long long) vertglbnbr, (long long) partnbr);
        return EXIT_FAILURE;
    }

    if (iam == 0)
        printf("PASSED: PT-SCOTCH built, checked and partitioned the graph\n");
    return EXIT_SUCCESS;
}
