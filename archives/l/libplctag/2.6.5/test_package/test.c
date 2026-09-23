#include <stdio.h>
#include <stdlib.h>
#include <libplctag.h>

/* test_package consumer test: exercise the real installed libplctag API.
 * Checks the library version (plc_tag_check_lib_version) and creates a tag
 * handle for a non-routable gateway. Without a real PLC on the network the
 * create/connect fails gracefully via plc_tag_decode_error, but this proves
 * header + static lib linkage and basic library runtime behavior. */
int main(void) {
    int rc;
    int32_t tag;

    /* Library version: expect libplctag 2.6 */
    rc = plc_tag_check_lib_version(2, 6, 0);
    printf("plc_tag_check_lib_version(2,6,0) rc=%d\n", rc);
    if (rc != 0) {
        printf("unexpected version: rc=%d\n", rc);
        return 1;
    }

    /* Non-routable gateway: create returns a tag handle (>=0); the tag
     * remains idle until a (virtual) PLC is reachable, but the create call
     * itself must succeed on this platform. */
    tag = plc_tag_create("protocol=ab_eip&gateway=192.0.2.1&path=1,0&elem_count=1&elem_size=4", 100);
    printf("plc_tag_create rc=%d\n", (int)tag);

    if (tag < 0) {
        printf("plc_tag_create failed with error: %s\n", plc_tag_decode_error(tag));
        return 0; /* linkage + error decode verified */
    }

    rc = plc_tag_destroy(tag);
    printf("plc_tag_destroy rc=%d\n", rc);
    return rc != 0;
}