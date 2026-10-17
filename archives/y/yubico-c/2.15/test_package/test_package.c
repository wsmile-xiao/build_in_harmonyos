/*
 * test_package.c — HarmonyOS consumer test for yubico-c (libykclient) 2.15.
 *
 * Per R34, this test substantively depends on the tested package:
 * it includes ykclient.h, links libykclient, and calls real API functions.
 *
 * HarmonyOS-specific checks (rule12):
 *   - ykclient_global_init() must succeed on HarmonyOS: this calls
 *     curl_global_init() on the cross-compiled libcurl/8.5.0, proving the
 *     OHOS toolchain build of the dependency chain loads and initialises.
 *   - Version consistency: header macro YKCLIENT_VERSION_STRING must match
 *     the runtime ykclient_check_version() return value.
 */
#include <stdio.h>
#include <string.h>

#include <ykclient.h>

int main(void) {
    /* HarmonyOS-specific: global init (curl_global_init on OHOS libcurl) */
    int ret = ykclient_global_init();
    if (ret != YKCLIENT_OK) {
        fprintf(stderr, "FAIL: ykclient_global_init() returned %d on HarmonyOS\n", ret);
        return 1;
    }
    printf("OK: ykclient_global_init() succeeded on HarmonyOS\n");

    /* Version consistency check */
    const char *ver = ykclient_check_version(NULL);
    if (ver == NULL) {
        fprintf(stderr, "FAIL: ykclient_check_version(NULL) returned NULL\n");
        return 1;
    }
    printf("OK: library version = %s\n", ver);

    if (strcmp(ver, YKCLIENT_VERSION_STRING) != 0) {
        fprintf(stderr, "FAIL: header version %s != library version %s\n",
                YKCLIENT_VERSION_STRING, ver);
        return 1;
    }
    printf("OK: header/library version match (%s)\n", ver);

    /* Version guard: requesting a future version returns NULL */
    if (ykclient_check_version("99.99.99") != NULL) {
        fprintf(stderr, "FAIL: ykclient_check_version(99.99.99) should return NULL\n");
        return 1;
    }
    printf("OK: version guard works (future version returns NULL)\n");

    /* Lifecycle: init / set client / done */
    ykclient_t *ykc = NULL;
    ret = ykclient_init(&ykc);
    if (ret != YKCLIENT_OK || ykc == NULL) {
        fprintf(stderr, "FAIL: ykclient_init() returned %d\n", ret);
        return 1;
    }
    printf("OK: ykclient_init() succeeded\n");

    /* Offline hex client key parsing */
    ret = ykclient_set_client_hex(ykc, 1, "deadbeef");
    if (ret != YKCLIENT_OK) {
        fprintf(stderr, "FAIL: ykclient_set_client_hex(deadbeef) returned %d\n", ret);
        return 1;
    }
    printf("OK: ykclient_set_client_hex(deadbeef) accepted\n");

    /* Invalid hex must fail */
    ret = ykclient_set_client_hex(ykc, 1, "xyz");
    if (ret != YKCLIENT_HEX_DECODE_ERROR) {
        fprintf(stderr, "FAIL: expected HEX_DECODE_ERROR, got %d\n", ret);
        return 1;
    }
    printf("OK: invalid hex correctly rejected\n");

    /* strerror sanity */
    if (strcmp(ykclient_strerror(YKCLIENT_OK), "Success") != 0) {
        fprintf(stderr, "FAIL: strerror(OK) mismatch\n");
        return 1;
    }
    printf("OK: ykclient_strerror works\n");

    ykclient_done(&ykc);
    ykclient_global_done();

    printf("All yubico-c (ykclient) HarmonyOS test assertions passed.\n");
    return 0;
}
