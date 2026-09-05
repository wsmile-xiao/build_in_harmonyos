/* test.c — substantive test of cctools libdttools API (R34)
 *
 * Calls debug() from libdttools to verify the library is installed
 * and linkable. debug() is the foundational logging function in
 * cctools (dttools/src/debug.c), declared in debug.h.
 */
#include <stdio.h>
#include "cctools/debug.h"

int main(void) {
    /* Initialize debug subsystem */
    debug_flags_set("all");
    debug_config("test_cctools");
    debug_config_file_size(0);  /* no rotation */

    /* Emit a debug message at D_DEBUG level */
    debug(D_DEBUG, "cctools libdttools linked successfully");

    /* Clean shutdown (do NOT call debug_config(NULL) — crashes on HarmonyOS) */
    debug_flags_clear();

    printf("test_cctools: OK (libdttools debug() called)\n");
    return 0;
}
