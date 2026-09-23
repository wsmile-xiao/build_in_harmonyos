#include <classencoder.h>
#include <pattern.h>

#include <iostream>
#include <vector>

int main() {
    ClassEncoder encoder;
    Pattern pattern = encoder.buildpattern("HarmonyOS PC", true, true);

    if (pattern.data == nullptr) return 1;
    if (pattern.n() != 2) return 2;
    if (pattern.bytesize() == 0) return 3;
    if (pattern.category() != NGRAM) return 4;

    std::vector<Pattern> unigrams;
    pattern.ngrams(unigrams, 1);
    if (unigrams.size() != 2) return 5;
    if (unigrams[0].n() != 1 || unigrams[1].n() != 1) return 6;

    std::cout << "colibri-core consumer test passed" << std::endl;
    return 0;
}
