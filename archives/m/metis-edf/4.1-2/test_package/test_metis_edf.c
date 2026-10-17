/*
 * Consumer test for metis-edf 4.1-2.
 *
 * Builds a small 4x4 grid graph in CSR form, partitions it with the two
 * partitioning entry points and computes a nested-dissection ordering with
 * METIS_NodeND (the routine used by the Code_Aster onmetis driver), checking
 * the structural properties of every result.
 */
#include <metis.h>

#include <stdio.h>
#include <stdlib.h>

static int g_checks;
static int g_fails;

static void check(int cond, const char *msg)
{
    g_checks++;
    if (cond) {
        printf("ok   - %s\n", msg);
    } else {
        g_fails++;
        printf("FAIL - %s\n", msg);
    }
}

/* 4x4 grid: 16 vertices, 24 undirected edges. */
static long build_grid(idxtype **xadj_out, idxtype **adjncy_out)
{
    const long rows = 4, cols = 4;
    const long n = rows * cols;
    idxtype *xadj = (idxtype *)calloc(n + 1, sizeof(idxtype));
    idxtype *adjncy = (idxtype *)calloc(4 * n, sizeof(idxtype));
    long i, k = 0;

    for (i = 0; i < n; i++) {
        long r = i / cols, c = i % cols;
        xadj[i] = (idxtype)k;
        if (c + 1 < cols) adjncy[k++] = (idxtype)(i + 1);
        if (r + 1 < rows) adjncy[k++] = (idxtype)(i + cols);
        if (c > 0)        adjncy[k++] = (idxtype)(i - 1);
        if (r > 0)        adjncy[k++] = (idxtype)(i - cols);
    }
    xadj[n] = (idxtype)k;
    *xadj_out = xadj;
    *adjncy_out = adjncy;
    return n;
}

static int is_permutation(const idxtype *p, long n)
{
    char *seen = (char *)calloc(n, sizeof(char));
    long i;
    int ok = 1;
    for (i = 0; i < n; i++) {
        if (p[i] < 0 || p[i] >= n || seen[p[i]]) {
            ok = 0;
            break;
        }
        seen[p[i]] = 1;
    }
    free(seen);
    return ok;
}

int main(void)
{
    idxtype *xadj, *adjncy, *part, *perm, *iperm;
    long nvtxs, wgtflag = 0, numflag = 0, nparts = 2, edgecut = 0;
    long options[10];
    long i, count[2];
    int seen[2];

    nvtxs = build_grid(&xadj, &adjncy);
    check(nvtxs == 16 && xadj[16] == 48,
          "grid graph built (16 vertices, 48 directed adjacency entries)");

    options[0] = 0;
    part = (idxtype *)malloc(nvtxs * sizeof(idxtype));

    METIS_PartGraphRecursive(&nvtxs, xadj, adjncy, NULL, NULL, &wgtflag,
                             &numflag, &nparts, options, &edgecut, part);
    check(edgecut >= 0, "METIS_PartGraphRecursive returned an edge cut");
    seen[0] = seen[1] = 0;
    for (i = 0; i < nvtxs; i++) {
        if (part[i] < 0 || part[i] >= nparts) break;
        seen[part[i]] = 1;
    }
    check(i == nvtxs, "recursive partition labels are all in [0, nparts)");
    check(seen[0] && seen[1], "recursive partition uses both subdomains");

    edgecut = 0;
    METIS_PartGraphKway(&nvtxs, xadj, adjncy, NULL, NULL, &wgtflag,
                        &numflag, &nparts, options, &edgecut, part);
    check(edgecut >= 0, "METIS_PartGraphKway returned an edge cut");
    count[0] = count[1] = 0;
    for (i = 0; i < nvtxs; i++) {
        if (part[i] >= 0 && part[i] < nparts)
            count[part[i]]++;
    }
    check(count[0] + count[1] == nvtxs, "kway partition covers every vertex");
    check(count[0] > 0 && count[1] > 0, "kway partition is non-empty");

    perm = (idxtype *)malloc(nvtxs * sizeof(idxtype));
    iperm = (idxtype *)malloc(nvtxs * sizeof(idxtype));
    METIS_NodeND(&nvtxs, xadj, adjncy, &numflag, options, perm, iperm);
    check(is_permutation(perm, nvtxs), "METIS_NodeND perm is a permutation");
    check(is_permutation(iperm, nvtxs), "METIS_NodeND iperm is a permutation");
    for (i = 0; i < nvtxs; i++) {
        if (perm[iperm[i]] != i) break;
    }
    check(i == nvtxs, "METIS_NodeND perm and iperm are inverse of each other");

    free(xadj);
    free(adjncy);
    free(part);
    free(perm);
    free(iperm);

    printf("metis-edf consumer checks: %d/%d passed\n",
           g_checks - g_fails, g_checks);
    return g_fails == 0 ? 0 : 1;
}
