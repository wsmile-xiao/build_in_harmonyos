#include <cstdlib>
#include <iostream>

#include "Cassiopee.h"

int main() {
    char sequence[] = CASSIOPEE_TEST_SEQUENCE;
    CassieIndexer indexer(sequence);
    indexer.index();

    CassieSearch searcher(&indexer);
    searcher.search("ggc");
    searcher.sort();
    if (searcher.matches.size() != 3) {
        std::cerr << "expected 3 matches, got " << searcher.matches.size() << '\n';
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
