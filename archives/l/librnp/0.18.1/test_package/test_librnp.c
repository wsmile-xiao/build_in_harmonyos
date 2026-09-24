/* test_package/test_librnp.c — substantive API test (R34).
 *
 * Links the packaged librnp and exercises its real C API:
 *  1. rnp_version_string() / rnp_version_string_full() non-empty
 *  2. rnp_version() matches rnp_version_for(0, 18, 1) + major/minor/patch
 *  3. rnp_backend_string()/rnp_backend_version() non-empty (Botan backend)
 *  4. rnp_supports_feature("symmetric algorithm", "AES256") supported
 *  5. rnp_ffi_create(GPG/GPG) + rnp_ffi_destroy round-trip
 *
 * Prints LIBRNP_TEST_RESULT passed=N total=N for the harness to parse.
 * If librnp were missing or broken, linking or an API call would fail.
 */
#include <rnp/rnp.h>

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    int total = 5;
    int passed = 0;

    const char *ver = rnp_version_string();
    if (ver && strlen(ver) > 0) {
        printf("version_string=%s\n", ver);
        passed++;
    } else {
        printf("FAIL: empty version_string\n");
    }

    const char *ver_full = rnp_version_string_full();
    unsigned ver_num = rnp_version();
    unsigned expect = rnp_version_for(0, 18, 1);
    if (ver_full && strlen(ver_full) > 0 && ver_num == expect
        && rnp_version_major(ver_num) == 0
        && rnp_version_minor(ver_num) == 18
        && rnp_version_patch(ver_num) == 1) {
        printf("version_full=%s version=0x%08x\n", ver_full, ver_num);
        passed++;
    } else {
        printf("FAIL: version mismatch full=%s got=0x%08x expect=0x%08x\n",
               ver_full ? ver_full : "(null)", ver_num, expect);
    }

    const char *backend = rnp_backend_string();
    const char *backend_ver = rnp_backend_version();
    if (backend && strlen(backend) > 0 && backend_ver && strlen(backend_ver) > 0) {
        printf("backend=%s %s\n", backend, backend_ver);
        passed++;
    } else {
        printf("FAIL: empty backend string\n");
    }

    {
        bool supported = false;
        rnp_result_t feat_ret = rnp_supports_feature("symmetric algorithm", "AES256", &supported);
        if (feat_ret == 0 && supported) {
            printf("AES256 supported\n");
            passed++;
        } else {
            printf("FAIL: AES256 not reported supported\n");
        }
    }

    {
        rnp_ffi_t ffi = NULL;
        if (rnp_ffi_create(&ffi, "GPG", "GPG") == 0 && ffi) {
            if (rnp_ffi_destroy(ffi) == 0) {
                printf("ffi create/destroy ok\n");
                passed++;
            } else {
                printf("FAIL: ffi destroy\n");
            }
        } else {
            printf("FAIL: ffi create\n");
        }
    }

    printf("LIBRNP_TEST_RESULT passed=%d total=%d\n", passed, total);
    if (passed != total) {
        printf("FAIL: %d/%d assertions passed\n", passed, total);
        return 1;
    }
    printf("test librnp 0.18.1: OK\n");
    return 0;
}
