// Self-contained translation unit for the clang-include-graph smoke run:
// no system/library headers, so libclang can parse it without any sysroot.
#include "graph_alpha.h"

int main()
{
    Alpha alpha;
    Beta beta;
    return alpha.value + beta.value;
}
