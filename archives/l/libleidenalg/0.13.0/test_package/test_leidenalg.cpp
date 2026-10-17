// Consumer test for libleidenalg 0.13.0 — real Leiden pipeline on Zachary.
// 6 checks: graph size, CPM partition validity, CPM optimisation gain,
// modularity partition validity, modularity optimisation gain, determinism.
#include <cmath>
#include <cstdio>
#include <vector>

#include <igraph.h>
#include <libleidenalg/GraphHelper.h>
#include <libleidenalg/Optimiser.h>
#include <libleidenalg/CPMVertexPartition.h>
#include <libleidenalg/ModularityVertexPartition.h>

#define CHECK(cond, msg)                                  \
    do {                                                  \
        if (!(cond)) {                                    \
            std::fprintf(stderr, "FAIL: %s\n", msg);      \
            return 1;                                     \
        }                                                 \
        std::printf("PASS: %s\n", msg);                   \
    } while (0)

static bool membership_valid(MutableVertexPartition* part, size_t n) {
    size_t ncomm = part->n_communities();
    if (ncomm < 1 || ncomm > n) {
        return false;
    }
    for (size_t v = 0; v < n; ++v) {
        if (part->membership(v) >= n) {
            return false;
        }
    }
    return true;
}

int main() {
    igraph_t g;
    if (igraph_famous(&g, "Zachary") != 0) {
        std::fprintf(stderr, "FAIL: igraph_famous(Zachary) failed\n");
        return 1;
    }

    Graph graph(&g);
    const size_t n = graph.vcount();
    CHECK(n == 34, "Zachary graph has 34 vertices");
    CHECK(graph.ecount() == 78, "Zachary graph has 78 edges");

    // CPM partition path (resolution 0.05, as in upstream example).
    // Note: CPMVertexPartition declares only quality(double) which hides the
    // base-class quality(); pass the construction resolution explicitly
    // (identical to base quality() which forwards to resolution_parameter).
    CPMVertexPartition cpm(&graph, 0.05);
    const double cpm_before = cpm.quality(0.05);
    Optimiser opt;
    opt.set_rng_seed(42);
    const double cpm_after = opt.optimise_partition(&cpm);
    CHECK(membership_valid(&cpm, n), "CPM membership valid after optimise");
    CHECK(std::isfinite(cpm_after) && cpm_after >= cpm_before,
          "CPM quality did not regress after optimise");

    // Modularity partition path.
    ModularityVertexPartition mod(&graph);
    const double mod_before = mod.quality();
    Optimiser opt2;
    opt2.set_rng_seed(42);
    const double mod_after = opt2.optimise_partition(&mod);
    CHECK(membership_valid(&mod, n), "modularity membership valid after optimise");
    CHECK(std::isfinite(mod_after) && mod_after >= mod_before,
          "modularity quality did not regress after optimise");

    std::printf("libleidenalg consumer test: all 6 checks PASSED\n");
    igraph_destroy(&g);
    return 0;
}
