#include <stdio.h>
#include <string.h>
#include "wren.h"

/* Consumer test: actually drive the Wren VM API (R34: must call the package API). */
int main(void) {
    WrenConfiguration config;
    wrenInitConfiguration(&config);
    config.initialHeapSize = 1024 * 1024 * 16;

    WrenVM* vm = wrenNewVM(&config);
    if (!vm) {
        fprintf(stderr, "wrenNewVM failed\n");
        return 1;
    }

    WrenInterpretResult result = wrenInterpret(
        vm, "main",
        "class Fib {\n"
        "  static compute(n) {\n"
        "    if (n < 2) return n\n"
        "    return compute(n-1) + compute(n-2)\n"
        "  }\n"
        "}\n"
        "System.print(Fib.compute(10))\n");
    if (result != WREN_RESULT_SUCCESS) {
        fprintf(stderr, "wrenInterpret failed: %d\n", (int)result);
        wrenFreeVM(vm);
        return 1;
    }

    wrenFreeVM(vm);
    printf("wren 0.4.0 consumer test: OK\n");
    return 0;
}