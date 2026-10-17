/* test_package for gpgme 1.24.0 — verifies libgpgme links and runs.
 * Calls gpgme_check_version() (returns the library version) and
 * gpgme_get_engine_info() / gpgme_set_engine_info for a real API check.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <gpgme.h>

int main(void)
{
    const char *ver;
    gpgme_error_t err;
    gpgme_engine_info_t info;

    ver = gpgme_check_version(NULL);
    if (!ver) {
        fprintf(stderr, "FAIL: gpgme_check_version() returned NULL\n");
        return 1;
    }
    if (strncmp(ver, "1.24", 4) != 0) {
        fprintf(stderr, "FAIL: unexpected gpgme version '%s'\n", ver);
        return 1;
    }
    printf("gpgme version: %s\n", ver);

    err = gpgme_get_engine_info(&info);
    if (err) {
        fprintf(stderr, "FAIL: gpgme_get_engine_info: %s\n", gpgme_strerror(err));
        return 1;
    }
    printf("gpgme engine info OK\n");

    return 0;
}
