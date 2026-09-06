#define SNOW_ENABLED
#define mkstemp snow_test_mkstemp
#include <snow/snow.h>

int snow_test_mkstemp(char *template)
{
    const char *expected = getenv("SNOW_EXPECTED_TMP_TEMPLATE");

    if (expected != NULL && strcmp(template, expected) == 0) {
        exit(EXIT_SUCCESS);
    }

    fprintf(stderr, "unexpected temporary path: %s\n", template);
    exit(EXIT_FAILURE);
}

snow_main();
