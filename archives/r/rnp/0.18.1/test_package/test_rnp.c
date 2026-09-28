#include <stdio.h>
#include <string.h>
#include <stdbool.h>

#include <rnp/rnp.h>

/* Consumer test: exercise the real librnp FFI.
 * Three deterministic checks, each prints one PASS line:
 * 1. rnp_version_string() is non-empty.
 * 2. rnp_backend_string()/rnp_backend_version() resolve (expect Botan 3 backend).
 * 3. rnp_ffi_create()/rnp_ffi_destroy() round-trip plus rnp_supports_feature query.
 */
int main(void) {
    int passed = 0;

    const char *ver = rnp_version_string();
    if (ver && ver[0] != '\0') {
        printf("CHECK version_string: PASS (%s)\n", ver);
        passed++;
    } else {
        printf("CHECK version_string: FAIL\n");
    }

    const char *backend = rnp_backend_string();
    const char *backend_ver = rnp_backend_version();
    if (backend && backend[0] != '\0' && backend_ver && backend_ver[0] != '\0') {
        printf("CHECK backend: PASS (%s %s)\n", backend, backend_ver);
        passed++;
    } else {
        printf("CHECK backend: FAIL\n");
    }

    rnp_ffi_t ffi = NULL;
    bool supported = false;
    if (rnp_ffi_create(&ffi, "GPG", "GPG") == 0 && ffi != NULL
        && rnp_supports_feature("symmetric algorithm", "AES256", &supported) == 0) {
        printf("CHECK ffi_create_supports: PASS (aes256 supported=%d)\n", (int) supported);
        passed++;
        rnp_ffi_destroy(ffi);
    } else {
        printf("CHECK ffi_create_supports: FAIL\n");
        if (ffi) {
            rnp_ffi_destroy(ffi);
        }
    }

    printf("SUMMARY passed=%d total=3\n", passed);
    return passed == 3 ? 0 : 1;
}
