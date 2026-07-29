#include <stdio.h>
#include "fast_float/fast_float.h"

int main() {
    double result = 0.0;
    auto ret = fast_float::from_chars("3.14", "3.14" + 4, result);
    if (ret.ec != std::errc{} || result != 3.14) {
        printf("test fast_float 7.0.0: FAILED (parse returned %d, result=%f)\n", (int)ret.ec, result);
        return 1;
    }
    printf("test fast_float 7.0.0: OK (result=%f)\n", result);
    return 0;
}
