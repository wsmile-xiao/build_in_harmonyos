#include <cpdb/cpdb.h>
#include <cpdb/frontend.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef __OHOS__
#error "This test validates the HarmonyOS package and must use the OHOS toolchain"
#endif

static void printer_changed(cpdb_frontend_obj_t *frontend,
                            cpdb_printer_obj_t *printer,
                            cpdb_printer_update_t update)
{
    (void)frontend;
    (void)printer;
    (void)update;
}

static int require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 0;
    }
    return 1;
}

int main(void)
{
    char *joined;
    cpdb_frontend_obj_t *frontend;

    cpdbInit();

    if (!require_true(sizeof(void *) == 8, "HarmonyOS AArch64 ABI"))
        return EXIT_FAILURE;
    if (!require_true(cpdbGetBoolean("true") == TRUE, "boolean true conversion"))
        return EXIT_FAILURE;
    if (!require_true(cpdbGetBoolean("false") == FALSE, "boolean false conversion"))
        return EXIT_FAILURE;

    joined = cpdbConcat("Harmony", "OS");
    if (!require_true(joined != NULL, "cpdbConcat allocation"))
        return EXIT_FAILURE;
    if (!require_true(strcmp(joined, "HarmonyOS") == 0, "cpdbConcat value")) {
        free(joined);
        return EXIT_FAILURE;
    }
    free(joined);

    frontend = cpdbGetNewFrontendObj("HarmonyOSTest", printer_changed);
    if (!require_true(frontend != NULL, "frontend creation"))
        return EXIT_FAILURE;
    if (!require_true(frontend->connection == NULL, "frontend initial D-Bus state")) {
        cpdbDeleteFrontendObj(frontend);
        return EXIT_FAILURE;
    }
    if (!require_true(frontend->printer != NULL, "frontend printer table")) {
        cpdbDeleteFrontendObj(frontend);
        return EXIT_FAILURE;
    }

    cpdbIgnoreLastSavedSettings(frontend);
    cpdbDeleteFrontendObj(frontend);
    puts("PASS: cpdb-libs HarmonyOS consumer API test");
    return EXIT_SUCCESS;
}
