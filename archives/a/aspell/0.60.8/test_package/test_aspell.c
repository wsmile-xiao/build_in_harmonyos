/*
 * test_aspell.c — validates aspell C API.
 *
 * R34: This test calls real aspell API functions:
 *   - new_aspell_config() — create a new AspellConfig
 *   - aspell_config_error() — check for errors
 *   - aspell_config_replace() — set a configuration key
 *   - aspell_config_retrieve() — get a configuration key value
 *   - delete_aspell_config() — free the config
 *
 * If any API call fails, the test exits with a non-zero code.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aspell.h"

int main(void)
{
    /* Create a new AspellConfig — this is the entry point to the aspell API */
    AspellConfig *config = new_aspell_config();
    if (!config) {
        fprintf(stderr, "FAIL: new_aspell_config() returned NULL\n");
        return 1;
    }
    printf("OK: new_aspell_config() succeeded\n");

    /* Check for errors on the fresh config */
    const AspellError *error = aspell_config_error(config);
    if (error) {
        fprintf(stderr, "FAIL: aspell_config_error() returned an error\n");
        delete_aspell_config(config);
        return 1;
    }
    printf("OK: aspell_config_error() returned no error\n");

    /* Set a configuration key — "lang" is a standard aspell config key */
    int ret = aspell_config_replace(config, "lang", "en");
    if (!ret) {
        fprintf(stderr, "FAIL: aspell_config_replace(lang, en) failed\n");
        delete_aspell_config(config);
        return 1;
    }
    printf("OK: aspell_config_replace(lang, en) succeeded\n");

    /* Verify the config key was set */
    const char *val = aspell_config_retrieve(config, "lang");
    if (!val || strcmp(val, "en") != 0) {
        fprintf(stderr, "FAIL: aspell_config_retrieve(lang) returned '%s'\n",
                val ? val : "(null)");
        delete_aspell_config(config);
        return 1;
    }
    printf("OK: aspell_config_retrieve(lang) = '%s'\n", val);

    /* Clean up */
    delete_aspell_config(config);
    printf("OK: delete_aspell_config() succeeded\n");

    printf("All aspell API tests passed.\n");
    return 0;
}
