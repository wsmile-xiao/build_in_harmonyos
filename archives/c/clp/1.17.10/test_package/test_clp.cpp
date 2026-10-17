#include <coin/ClpSimplex.hpp>
#include <cstdio>

int main() {
    ClpSimplex model;
    model.setOptimizationDirection(-1.0);
    if (model.optimizationDirection() != -1.0) {
        std::fprintf(stderr, "ClpSimplex optimization direction round-trip failed\n");
        return 1;
    }
    std::printf("test clp 1.17.10: OK\n");
    return 0;
}
