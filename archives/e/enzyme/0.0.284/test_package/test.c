/* test.c — R34 genuine dependency check.
   Receives ENZYME_PLUGIN_LIB from conanfile.py (actual path to
   libLLVMEnzyme-15.so), runs nm symbol presence check.
   Returns 1 if nm fails or symbol not found — no false pass.
   L1e sabotage (lib/ removed) → nm can't find .so → return 1 →
   genuine dependency confirmed (no false pass). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    const char *lib_path = getenv("ENZYME_PLUGIN_LIB");
    if (!lib_path || !lib_path[0]) {
        fprintf(stderr, "FAIL: ENZYME_PLUGIN_LIB not set\n");
        return 1;
    }
    /* Build nm command: nm -D <path> | grep -q llvmGetPassPluginInfo */
    char cmd[4096];
    int n = snprintf(cmd, sizeof(cmd),
        "/data/service/hnp/bin/nm -D \"%s\" 2>/dev/null | "
        "grep -q \"llvmGetPassPluginInfo\"", lib_path);
    if (n < 0 || (size_t)n >= sizeof(cmd)) {
        fprintf(stderr, "FAIL: cmd buffer overflow\n");
        return 1;
    }
    int rc = system(cmd);
    if (rc != 0) {
        fprintf(stderr, "FAIL: nm symbol check failed (exit %d) for %s\n", rc, lib_path);
        fprintf(stderr, "       llvmGetPassPluginInfo not found in plugin library\n");
        return 1;
    }
    printf("test enzyme 0.0.284: OK (ENZYME_PLUGIN_LIB=%s, llvmGetPassPluginInfo present)\n", lib_path);
    return 0;
}