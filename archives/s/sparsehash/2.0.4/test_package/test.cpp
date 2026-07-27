#include <sparsehash/dense_hash_map>
#include <sparsehash/sparse_hash_map>

#include <iostream>
#include <string>

int main() {
    google::sparse_hash_map<int, std::string> sparse;
    sparse.set_deleted_key(-1);
    sparse[7] = "HarmonyOS";
    sparse[42] = "sparsehash";

    const auto found = sparse.find(7);
    if (sparse.size() != 2 || found == sparse.end() || found->second != "HarmonyOS") {
        std::cerr << "sparse_hash_map insertion failed" << std::endl;
        return 1;
    }
    if (sparse.count(42) != 1 || sparse.count(99) != 0) {
        std::cerr << "sparse_hash_map lookup failed" << std::endl;
        return 2;
    }
    if (sparse.erase(42) != 1 || sparse.count(42) != 0) {
        std::cerr << "sparse_hash_map erase failed" << std::endl;
        return 3;
    }

    google::dense_hash_map<int, int> dense;
    dense.set_empty_key(-1);
    dense.set_deleted_key(-2);
    dense[1] = 10;
    dense[2] = 20;

    if (dense.size() != 2 || dense[1] + dense[2] != 30) {
        std::cerr << "dense_hash_map insertion failed" << std::endl;
        return 4;
    }
    if (dense.erase(1) != 1 || dense.count(1) != 0) {
        std::cerr << "dense_hash_map erase failed" << std::endl;
        return 5;
    }

    std::cout << "sparsehash consumer test passed" << std::endl;
    return 0;
}
