/* Upstream smoke for rankwidth 0.10 -- igraph-free driver for the bundled
 * example graphs, promoted to a real on-device upstream regression.
 *
 * Provenance (verbatim sources, adaptation noted):
 * - Upstream tag: rw-0.10.tar.gz (355838 bytes, sha256
 *   89a8ed364893ac1b70ab70a152e3e7db3cf348bb69098aa6dbb969639df927db).
 * - Core compute loop verbatim from upstream simplerw.c main():
 *     for (i = 0; i <= num_vertices; i++) calculate_level(i);
 *     get_rw(); destroy_rw();
 *   plus set_am()/bitmask() helpers verbatim from simplerw.c.
 * - Smoke command verbatim from upstream README:
 *     "rw --edgelist example_graphs/igrid"
 *   README states rw.h/rw.c provide the mechanism and simplerw.c the CLI.
 * - Adaptation (minimal, documented): upstream read_graph() needs igraph
 *   (>= 0.6, PKG_CHECK_MODULES) which the library-only adaptation disables
 *   (--disable-executable, Gentoo rw-0.10 ebuild precedent: "executable
 *   depends on igraph"). igraph is not published to the ohpcd artefact
 *   repository, so file input is replaced by a minimal edgelist parser
 *   (blank/# lines skipped, "u v" per line) that feeds the same
 *   adjacency_matrix + init_rw_dec/calculate_level/get_rw/destroy_rw path.
 *   No upstream logic is skipped: every edge in the vendored data files
 *   is loaded, every level 0..n is calculated.
 * - Data files vendored verbatim from rw-0.10/example_graphs/:
 *   grid.edgelist (50 bytes), igrid.edgelist (358 bytes),
 *   hangematte.edgelist (110 bytes, ascii-renamed from "H\xc3\xa4ngematte"
 *   to avoid non-ASCII filename issues; bytes identical).
 *
 * Exit-code oracle: 0 = graph loaded, all levels calculated, rank-width
 * in [0, n]; non-zero = any failure (message on stderr). No stdout
 * string counting is used for the verdict.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "rw.h"

static unsigned g_n = 0;

static uint_fast32_t bitmask(int i)
{
    return (1ul << i);
}

static void set_am(int i, int j, int val)
{
    adjacency_matrix[i] &= ~bitmask(j);
    adjacency_matrix[j] &= ~bitmask(i);
    if (val) {
        adjacency_matrix[i] |= bitmask(j);
        adjacency_matrix[j] |= bitmask(i);
    }
}

int main(int argc, char *argv[])
{
    static int eu[1024];
    static int ev[1024];
    int nedges = 0;
    int maxv = -1;
    FILE *f;
    char line[256];

    if (argc != 2) {
        fprintf(stderr, "Usage: %s <edgelist-file>\n", argc > 0 ? argv[0] : "upstream_smoke");
        return 2;
    }
    f = fopen(argv[1], "r");
    if (!f) {
        fprintf(stderr, "SMOKE FAIL: cannot open %s\n", argv[1]);
        return 1;
    }
    while (fgets(line, sizeof(line), f)) {
        char *p = line;
        int u, v, nch;
        while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')
            p++;
        if (*p == '\0' || *p == '#')
            continue;
        if (sscanf(p, "%d %d %n", &u, &v, &nch) != 2) {
            /* Skip separator/blank lines (igrid uses blank lines between blocks). */
            continue;
        }
        if (u < 0 || v < 0 || u > 31 || v > 31) {
            fprintf(stderr, "SMOKE FAIL: vertex out of range u=%d v=%d (file %s)\n", u, v, argv[1]);
            fclose(f);
            return 1;
        }
        if (nedges >= (int)(sizeof(eu) / sizeof(eu[0]))) {
            fprintf(stderr, "SMOKE FAIL: too many edges (file %s)\n", argv[1]);
            fclose(f);
            return 1;
        }
        eu[nedges] = u;
        ev[nedges] = v;
        nedges++;
        if (u > maxv)
            maxv = u;
        if (v > maxv)
            maxv = v;
    }
    fclose(f);
    if (maxv < 0) {
        fprintf(stderr, "SMOKE FAIL: no edges parsed (file %s)\n", argv[1]);
        return 1;
    }
    g_n = (unsigned)(maxv + 1);
    if (g_n < 1 || g_n > 32) {
        fprintf(stderr, "SMOKE FAIL: bad vertex count n=%u (file %s)\n", g_n, argv[1]);
        return 1;
    }
    if (init_rw_dec((uint_fast8_t)g_n) != 0) {
        fprintf(stderr, "SMOKE FAIL: init_rw_dec(%u) != 0 (file %s)\n", g_n, argv[1]);
        return 1;
    }
    /* Fully define the symmetric adjacency matrix (same pattern as
     * simplerw.c read_graph: nested full i/j loop so malloc garbage
     * cannot survive). */
    {
        static char adj[32][32];
        int i, j, k;
        memset(adj, 0, sizeof(adj));
        for (k = 0; k < nedges; k++) {
            adj[eu[k]][ev[k]] = 1;
            adj[ev[k]][eu[k]] = 1;
        }
        for (i = 0; i < (int)g_n; i++)
            for (j = 0; j < (int)g_n; j++)
                set_am(i, j, adj[i][j]);
    }
    /* Verbatim compute loop from simplerw.c main(). */
    {
        int i;
        for (i = 0; i <= (int)g_n; i++)
            calculate_level((uint_fast8_t)i);
    }
    {
        unsigned rw = (unsigned)get_rw();
        printf("SMOKE PASS file=%s n=%u edges=%d rank-width=%u\n", argv[1], g_n, nedges, rw);
        if (rw > g_n) {
            fprintf(stderr, "SMOKE FAIL: rank-width %u > n %u (file %s)\n", rw, g_n, argv[1]);
            destroy_rw();
            return 1;
        }
    }
    destroy_rw();
    return 0;
}
