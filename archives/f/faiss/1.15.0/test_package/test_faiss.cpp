// test_faiss.cpp - Verify FAISS library API works correctly
#include <faiss/IndexFlat.h>
#include <cstdio>
#include <vector>

int main() {
    int d = 4;       // dimension
    int nb = 5;      // database size
    int nq = 2;      // number of queries

    // Generate some test data
    std::vector<float> database(nb * d);
    for (int i = 0; i < nb * d; i++) {
        database[i] = static_cast<float>(i) * 0.1f;
    }

    // Create L2 index
    faiss::IndexFlatL2 index_l2(d);
    index_l2.add(nb, database.data());
    printf("L2 index: ntotal=%ld, d=%d\n", (long)index_l2.ntotal, index_l2.d);

    // Search
    std::vector<float> queries(nq * d);
    for (int i = 0; i < nq * d; i++) {
        queries[i] = static_cast<float>(i) * 0.1f;
    }
    int k = 3;
    std::vector<float> distances(nq * k);
    std::vector<faiss::idx_t> labels(nq * k);
    index_l2.search(nq, queries.data(), k, distances.data(), labels.data());

    printf("L2 search results (k=%d):\n", k);
    for (int i = 0; i < nq; i++) {
        printf("  query %d:", i);
        for (int j = 0; j < k; j++) {
            printf(" [label=%ld, dist=%.4f]", (long)labels[i * k + j], distances[i * k + j]);
        }
        printf("\n");
    }

    // Test 2: Inner product index
    faiss::IndexFlatIP index_ip(d);
    index_ip.add(nb, database.data());
    index_ip.search(nq, queries.data(), k, distances.data(), labels.data());
    printf("IP search completed, ntotal=%ld\n", (long)index_ip.ntotal);

    // Verify results
    if (index_l2.ntotal != nb) {
        printf("FAIL: expected ntotal=%d, got %ld\n", nb, (long)index_l2.ntotal);
        return 1;
    }
    if (labels[0] == -1) {
        printf("FAIL: first search result label is -1\n");
        return 1;
    }

    printf("PASS: FAISS library works correctly\n");
    return 0;
}
