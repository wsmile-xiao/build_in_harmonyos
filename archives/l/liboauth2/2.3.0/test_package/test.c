/*
 * test_package smoke test for liboauth2
 * Verifies the library links and core APIs are callable.
 */
#include <stdio.h>
#include <string.h>
#include <oauth2/version.h>
#include <oauth2/log.h>

int main(void)
{
    const char *ver = oauth2_version();
    if (ver == NULL || strlen(ver) == 0) {
        fprintf(stderr, "FAIL: oauth2_version() returned NULL or empty\n");
        return 1;
    }
    printf("liboauth2 version: %s\n", ver);

    /* Verify log level enum is accessible */
    oauth2_log_level_t level = OAUTH2_LOG_WARN;
    (void)level;

    printf("PASS: liboauth2 test_package succeeded\n");
    return 0;
}
