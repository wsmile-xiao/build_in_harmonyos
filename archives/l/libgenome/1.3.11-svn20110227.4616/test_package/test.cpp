#include <libGenome/gnSequence.h>

#include <cstdio>
#include <string>

int main() {
    genome::gnSequence sequence("ATGCC");
    if (sequence.length() != 5) {
        return 1;
    }
    if (sequence.ToString() != std::string("ATGCC")) {
        return 2;
    }
    genome::gnGenomeSpec* spec = sequence.GetSpec();
    if (spec == 0) {
        return 3;
    }
    spec->SetReverseComplement(true);
    if (sequence.ToString() != std::string("GGCAT")) {
        return 4;
    }
    std::puts("libgenome reverse-complement consumer: PASS");
    return 0;
}
