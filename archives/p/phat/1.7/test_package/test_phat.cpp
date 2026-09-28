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

phat::boundary_matrix<phat::vector_vector> triangle() {
    phat::boundary_matrix<phat::vector_vector> matrix;
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
    const phat::boundary_matrix<phat::vector_vector> original = triangle();
    check(original.get_num_cols() == 7, "column count", checks);
    check(original.get_num_entries() == 9, "boundary entry count", checks);

    phat::boundary_matrix<phat::vector_vector> standard_matrix(original);
    phat::persistence_pairs standard_pairs;
    phat::compute_persistence_pairs<phat::standard_reduction>(
        standard_pairs, standard_matrix);
    standard_pairs.sort();
    check(standard_pairs.get_num_pairs() == 3, "persistence pair count", checks);
    check(standard_pairs.get_pair(0) == std::make_pair(static_cast<phat::index>(1), static_cast<phat::index>(3)),
          "first persistence pair", checks);
    check(standard_pairs.get_pair(1) == std::make_pair(static_cast<phat::index>(2), static_cast<phat::index>(4)),
          "second persistence pair", checks);
    check(standard_pairs.get_pair(2) == std::make_pair(static_cast<phat::index>(5), static_cast<phat::index>(6)),
          "third persistence pair", checks);

    phat::boundary_matrix<phat::vector_vector> twist_matrix(original);
    phat::persistence_pairs twist_pairs;
    phat::compute_persistence_pairs<phat::twist_reduction>(twist_pairs, twist_matrix);
    twist_pairs.sort();
    check(twist_pairs == standard_pairs, "twist and standard agree", checks);

    phat::boundary_matrix<phat::vector_vector> chunk_matrix(original);
    phat::persistence_pairs chunk_pairs;
    phat::compute_persistence_pairs<phat::chunk_reduction>(chunk_pairs, chunk_matrix);
    chunk_pairs.sort();
    check(chunk_pairs == standard_pairs, "chunk and standard agree", checks);

    std::cout << "PHAT generic consumer checks passed: " << checks << std::endl;
    return EXIT_SUCCESS;
}
