#include <aalib.h>

int main() {
    if (aa_defparams.width <= 0 || aa_defparams.height <= 0) return 1;
    if (aa_dithernames[0] == nullptr) return 2;
    return 0;
}
