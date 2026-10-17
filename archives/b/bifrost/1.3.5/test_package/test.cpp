// Conan L1 official test — must actually exercise the packaged library.
// Includes only the installed public headers (<bifrost/...>), builds a
// CompactedDBG graph from a small FASTA via the public CDBG_Build_opt /
// build() API and verifies a real k-mer lookup through find() (R34).
#include <bifrost/CompactedDBG.hpp>
#include <bifrost/Kmer.hpp>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

int main() {
    const int k = 31;
    const std::string seq =
        "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT"
        "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT";

    // Write a tiny FASTA input in the current (writable) build dir.
    const std::string fasta = "test_input.fasta";
    {
        std::ofstream f(fasta.c_str(), std::ios::out);
        f << ">seq1\n" << seq << "\n";
    }

    CompactedDBG<> graph(k);

    CDBG_Build_opt opt;
    opt.verbose = false;
    opt.nb_threads = 1;
    opt.k = k;
    opt.build = true;
    opt.filename_seq_in = std::vector<std::string>{fasta};

    if (!graph.build(opt)) {
        std::cerr << "graph.build failed" << std::endl;
        return 2;
    }

    if (graph.getK() != k) {
        std::cerr << "unexpected k: " << graph.getK() << std::endl;
        return 3;
    }

    // Look up the head k-mer of the input sequence through the public API.
    const Kmer km(seq.substr(0, k).c_str());
    const auto um = graph.find(km);
    if (!um.isEmpty) {
        std::cout << "bifrost consumer OK: graph k=" << graph.getK()
                  << ", head k-mer found, unitig length " << um.dist
                  << std::endl;
        std::remove(fasta.c_str());
        return 0;
    }

    std::cerr << "head k-mer not found in graph" << std::endl;
    std::remove(fasta.c_str());
    return 4;
}
