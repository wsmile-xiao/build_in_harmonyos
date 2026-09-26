#include <cpdb-libs-frontend.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef __OHOS__
#error "This test validates the HarmonyOS package and must use the OHOS toolchain"
#endif

static int printer_changed(PrinterObj *printer)
{
    (void)printer;
    return 0;
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
    char *copy;
    Settings *settings;
    FrontendObj *frontend;
    int checked = 0;

    if (!require_true(sizeof(void *) == 8, "HarmonyOS AArch64 ABI"))
        return EXIT_FAILURE;
    checked++;

    if (!require_true(get_boolean("true") == TRUE, "boolean true conversion"))
        return EXIT_FAILURE;
    checked++;
    if (!require_true(get_boolean("false") == FALSE, "boolean false conversion"))
        return EXIT_FAILURE;
    checked++;

    copy = get_string_copy("HarmonyOS");
    if (!require_true(copy != NULL, "get_string_copy allocation"))
        return EXIT_FAILURE;
    checked++;
    if (!require_true(strcmp(copy, "HarmonyOS") == 0, "get_string_copy value")) {
        free(copy);
        return EXIT_FAILURE;
    }
    free(copy);
    checked++;

    settings = get_new_Settings();
    if (!require_true(settings != NULL, "settings creation"))
        return EXIT_FAILURE;
    checked++;
    if (!require_true(settings->table != NULL, "settings table allocation")) {
        delete_Settings(settings);
        return EXIT_FAILURE;
    }
    checked++;
    add_setting(settings, CPD_OPTION_COPIES, "2");
    if (!require_true(g_hash_table_size(settings->table) == 1,
                      "add_setting stores the setting")) {
        delete_Settings(settings);
        return EXIT_FAILURE;
    }
    checked++;
    if (!require_true(clear_setting(settings, CPD_OPTION_COPIES) == TRUE,
                      "clear_setting removes the setting")) {
        delete_Settings(settings);
        return EXIT_FAILURE;
    }
    checked++;
    delete_Settings(settings);

    frontend = get_new_FrontendObj("HarmonyOSTest", printer_changed, printer_changed);
    if (!require_true(frontend != NULL, "frontend creation"))
        return EXIT_FAILURE;
    checked++;
    if (!require_true(frontend->connection == NULL, "frontend initial D-Bus state")) {
        return EXIT_FAILURE;
    }
    checked++;
    if (!require_true(frontend->printer != NULL, "frontend printer table")) {
        return EXIT_FAILURE;
    }
    checked++;

    printf("PASS: cpdb-libs 1.2.0 HarmonyOS consumer API test (%d assertions)\n",
           checked);
    return EXIT_SUCCESS;
}