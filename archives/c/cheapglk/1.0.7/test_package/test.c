#include <stdio.h>
#include <stdlib.h>
#include <glk.h>
#include <glkstart.h>

/* CheapGlk ships its own main() in main.o; the test program provides the
   three user callbacks it requires (glk_main / glkunix_arguments /
   glkunix_startup_code). */

/* Glk spec version reported by cheapglk 1.0.7: cggestal.c answers
   gestalt_Version with 0x00000706 (Glk spec 0.7.6). Asserting the exact
   value keeps this a real gate instead of a check that can never fail. */
#define CHEAPGLK_EXPECTED_GESTALT_VERSION 0x00000706u

static glui32 glk_gestalt_version_query(void) {
    /* glk_gestalt is a pure query; it never exits the process. */
    return glk_gestalt(gestalt_Version, 0);
}

void glk_main(void) {
    glui32 version = glk_gestalt_version_query();
    if (version != CHEAPGLK_EXPECTED_GESTALT_VERSION) {
        /* Report the failure and make it visible to the CI gate.
           glk_exit() cannot carry a status here: glk.h declares
           `extern void glk_exit(void)` (GLK_ATTRIBUTE_NORETURN) and
           cheapglk's cgmisc.c implementation is hard-wired to exit(0),
           so the failing path has to exit(1) itself. */
        printf("cheapglk test FAILED: glk_gestalt(gestalt_Version) = 0x%08X, "
               "expected 0x%08X\n",
               version, CHEAPGLK_EXPECTED_GESTALT_VERSION);
        exit(1);
    }
    printf("cheapglk 1.0.7: OK (Glk spec version 0x%08X)\n", version);
}

glkunix_argumentlist_t glkunix_arguments[] = {
    { NULL, glkunix_arg_End, NULL }
};

int glkunix_startup_code(glkunix_startup_t *data) {
    return TRUE;
}
