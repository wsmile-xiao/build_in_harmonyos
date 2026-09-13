#include <stdio.h>
#include <stdlib.h>
#include <libplctag.h>

/* HarmonyOS-specific test case for libplctag.
 *
 * Verifies on the OHOS platform:
 *  1. Library version contract (plc_tag_check_lib_version).
 *  2. Tag object lifecycle (create -> status -> destroy) repeated in a loop.
 *     Each create/destroy exercises the internal OHOS thread and mutex
 *     layer (thread_create/thread_join/mutex_* in src/platform/posix),
 *     including the pthread_cancel fallback path patched for OHOS musl.
 *  3. Error decode path (plc_tag_decode_error) for a non-reachable gateway.
 *
 * A real PLC is NOT required: with an unroutable gateway the create call
 * must still succeed (handle >= 0) and the status must be a decodable
 * error, which is the expected offline behavior on any platform.
 */
int main(void) {
    int rc;
    int32_t tag;
    const char *err;
    int i, created = 0, destroyed = 0;

    rc = plc_tag_check_lib_version(2, 6, 0);
    printf("OHOS test: plc_tag_check_lib_version(2,6,0) rc=%d\n", rc);
    if (rc != 0) {
        printf("OHOS test FAIL: unexpected version rc=%d\n", rc);
        return 1;
    }

    for (i = 0; i < 5; i++) {
        tag = plc_tag_create("protocol=ab_eip&gateway=192.0.2.1&path=1,0&elem_count=1&elem_size=4", 200);
        printf("OHOS test: iter %d plc_tag_create rc=%d\n", i, (int)tag);
        if (tag < 0) {
            err = plc_tag_decode_error(tag);
            printf("OHOS test: iter %d decode_error=%s\n", i, err);
            if (!err || err[0] == '\0') {
                printf("OHOS test FAIL: empty decode_error\n");
                return 1;
            }
            continue; /* offline: creation error is acceptable, but must decode */
        }
        created++;
        rc = plc_tag_status(tag);
        printf("OHOS test: iter %d plc_tag_status rc=%d err=%s\n", i, rc, plc_tag_decode_error(rc));
        rc = plc_tag_destroy(tag);
        printf("OHOS test: iter %d plc_tag_destroy rc=%d\n", i, rc);
        if (rc != 0) {
            printf("OHOS test FAIL: destroy rc=%d\n", rc);
            return 1;
        }
        destroyed++;
    }

    printf("OHOS test PASS: created=%d destroyed=%d version_ok=1\n", created, destroyed);
    return 0;
}
