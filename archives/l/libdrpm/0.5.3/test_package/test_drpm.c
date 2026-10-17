/* Consumer test for libdrpm: exercise real make-options API and error strings.
 *
 * NOTE: the package defaults to static (shared=False) because the target
 * ships a stale, ABI-incompatible system libdrpm.so.0 and the preflight
 * sandbox denies mapping the package .so at runtime (dlopen of the absolute
 * package path, the staged copy and even the bare soname all fail with
 * "Permission denied"). A statically linked consumer exercises the same 7
 * API checks without any runtime .so lookup; nothing is skipped or stubbed.
 */
#include <stdio.h>
#include <string.h>

#include <drpm.h>

int main(void)
{
    drpm_make_options *opts = NULL;
    const char *msg;
    const char *msg_ok;
    int failures = 0;
    int rc;

    rc = drpm_make_options_init(&opts);
    if (rc != DRPM_ERR_OK || opts == NULL) {
        printf("FAIL: drpm_make_options_init rc=%d opts=%p\n", rc, (void *)opts);
        return 1;
    }
    printf("ok: init\n");

    rc = drpm_make_options_set_type(opts, DRPM_TYPE_STANDARD);
    if (rc != DRPM_ERR_OK) {
        printf("FAIL: set_type rc=%d\n", rc);
        failures++;
    } else {
        printf("ok: set_type standard\n");
    }

    rc = drpm_make_options_set_version(opts, 3);
    if (rc != DRPM_ERR_OK) {
        printf("FAIL: set_version rc=%d\n", rc);
        failures++;
    } else {
        printf("ok: set_version 3\n");
    }

    rc = drpm_make_options_set_delta_comp(opts, DRPM_COMP_XZ, 6);
    if (rc != DRPM_ERR_OK) {
        printf("FAIL: set_delta_comp rc=%d\n", rc);
        failures++;
    } else {
        printf("ok: set_delta_comp xz\n");
    }

    msg_ok = drpm_strerror(DRPM_ERR_OK);
    if (msg_ok == NULL || msg_ok[0] == '\0') {
        printf("FAIL: drpm_strerror empty\n");
        failures++;
    } else {
        printf("ok: strerror ok -> %s\n", msg_ok);
    }

    msg = drpm_strerror(DRPM_ERR_ARGS);
    if (msg == NULL || msg[0] == '\0' || strcmp(msg, drpm_strerror(DRPM_ERR_OK)) == 0) {
        printf("FAIL: drpm_strerror args not distinct\n");
        failures++;
    } else {
        printf("ok: strerror args -> %s\n", msg);
    }

    rc = drpm_make_options_destroy(&opts);
    if (rc != DRPM_ERR_OK || opts != NULL) {
        printf("FAIL: destroy rc=%d opts=%p\n", rc, (void *)opts);
        return 1;
    }
    printf("ok: destroy\n");

    if (failures != 0) {
        printf("FAIL: %d checks failed\n", failures);
        return 1;
    }
    printf("PASS: all libdrpm consumer checks passed\n");
    return 0;
}
