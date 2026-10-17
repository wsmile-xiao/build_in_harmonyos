#include <stdio.h>
#include <system_error>
#include "fast_float/fast_float.h"

int main() {
    double result = 0.0;
    auto ret = fast_float::from_chars("3.14", "3.14" + 4, result);
    if (ret.ec != std::errc{} || result != 3.14) {
        printf("test fast_float 6.1.6: FAILED (parse returned %d, result=%f)\n", (int)ret.ec, result);
        return 1;
    }
    printf("test fast_float 6.1.6: OK (result=%f)\n", result);
    return 0;
}