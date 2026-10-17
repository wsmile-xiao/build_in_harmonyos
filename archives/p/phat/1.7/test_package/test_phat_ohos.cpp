#ifndef __OHOS__
#error "This test must be compiled for HarmonyOS"
#endif

#ifndef __aarch64__
#error "This test must be compiled for AArch64"
#endif

#include <cstdlib>
#include <iostream>
#include <vector>

#include <phat/algorithms/chunk_reduction.h>
#include <phat/algorithms/standard_reduction.h>
#include <phat/algorithms/twist_reduction.h>
#include <phat/compute_persistence_pairs.h>
#include <phat/representations/default_representations.h>

namespace {

void check(bool condition, const char* message, int& checks) {
    ++checks;
    if (!condition) {
        std::cerr << "FAIL: " << message << std::endl;
        std::exit(EXIT_FAILURE);
    }
}

phat::boundary_matrix<phat::bit_tree_pivot_column> triangle() {
    phat::boundary_matrix<phat::bit_tree_pivot_column> matrix;
    matrix.set_num_cols(7);
    const phat::dimension dimensions[] = {0, 0, 0, 1, 1, 1, 2};
    const phat::index entries[][3] = {
        {-1, -1, -1}, {-1, -1, -1}, {-1, -1, -1}, {0, 1, -1},
        {0, 2, -1}, {1, 2, -1}, {3, 4, 5},
    };
    const int sizes[] = {0, 0, 0, 2, 2, 2, 3};
    for (phat::index column = 0; column < 7; ++column) {
        matrix.set_dim(column, dimensions[column]);
        std::vector<phat::index> boundary;
        for (int entry = 0; entry < sizes[column]; ++entry) {
            boundary.push_back(entries[column][entry]);
        }
        matrix.set_col(column, boundary);
    }
    return matrix;
}

}  // namespace

int main() {
    int checks = 0;
    const phat::boundary_matrix<phat::bit_tree_pivot_column> original = triangle();
    check(sizeof(phat::index) == 8, "64-bit PHAT index ABI", checks);
    check(original.get_num_cols() == 7, "AArch64 column count", checks);
    check(original.get_num_entries() == 9, "AArch64 entry count", checks);

    phat::boundary_matrix<phat::bit_tree_pivot_column> standard_matrix(original);
    phat::persistence_pairs standard_pairs;
    phat::compute_persistence_pairs<phat::standard_reduction>(
        standard_pairs, standard_matrix);
    check(standard_pairs.get_num_pairs() == 3, "standard reduction pair count", checks);

    phat::boundary_matrix<phat::bit_tree_pivot_column> twist_matrix(original);
    phat::persistence_pairs twist_pairs;
    phat::compute_persistence_pairs<phat::twist_reduction>(twist_pairs, twist_matrix);
    check(twist_pairs == standard_pairs, "twist reduction agrees", checks);

    phat::boundary_matrix<phat::bit_tree_pivot_column> chunk_matrix(original);
    phat::persistence_pairs chunk_pairs;
    phat::compute_persistence_pairs<phat::chunk_reduction>(chunk_pairs, chunk_matrix);
    check(chunk_pairs == standard_pairs, "chunk reduction agrees", checks);

    std::cout << "PHAT HarmonyOS AArch64 checks passed: " << checks << std::endl;
    return EXIT_SUCCESS;
}
