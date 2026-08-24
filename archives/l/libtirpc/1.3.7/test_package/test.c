#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <tirpc/rpc/types.h>
#include <tirpc/rpc/xdr.h>

int main(void) {
    /* Test 1: XDR integer encoding/decoding */
    xdrproc_t proc = (xdrproc_t)xdr_int;
    XDR xdrs;
    char buf[1024];
    int original = 42;
    int decoded = 0;
    size_t size;

    memset(buf, 0, sizeof(buf));
    xdrmem_create(&xdrs, buf, sizeof(buf), XDR_ENCODE);
    if (!proc(&xdrs, &original)) {
        fprintf(stderr, "FAIL: xdr_int encode failed\n");
        return 1;
    }
    size = xdr_getpos(&xdrs);
    xdr_destroy(&xdrs);

    xdrmem_create(&xdrs, buf, size, XDR_DECODE);
    if (!proc(&xdrs, &decoded)) {
        fprintf(stderr, "FAIL: xdr_int decode failed\n");
        return 1;
    }
    xdr_destroy(&xdrs);

    if (decoded != original) {
        fprintf(stderr, "FAIL: xdr_int roundtrip mismatch: %d != %d\n", decoded, original);
        return 1;
    }
    printf("PASS: xdr_int roundtrip (%d == %d)\n", original, decoded);

    /* Test 2: XDR string encoding/decoding */
    xdrproc_t str_proc = (xdrproc_t)xdr_wrapstring;
    char *test_str = "libtirpc";
    char *decoded_str = NULL;
    size_t str_size;

    memset(buf, 0, sizeof(buf));
    xdrmem_create(&xdrs, buf, sizeof(buf), XDR_ENCODE);
    if (!str_proc(&xdrs, &test_str)) {
        fprintf(stderr, "FAIL: xdr_wrapstring encode failed\n");
        return 1;
    }
    str_size = xdr_getpos(&xdrs);
    xdr_destroy(&xdrs);

    xdrmem_create(&xdrs, buf, str_size, XDR_DECODE);
    if (!str_proc(&xdrs, &decoded_str)) {
        fprintf(stderr, "FAIL: xdr_wrapstring decode failed\n");
        return 1;
    }
    xdr_destroy(&xdrs);

    if (strcmp(decoded_str, test_str) != 0) {
        fprintf(stderr, "FAIL: xdr_wrapstring roundtrip mismatch: %s != %s\n",
                decoded_str, test_str);
        return 1;
    }
    printf("PASS: xdr_wrapstring roundtrip (%s == %s)\n", test_str, decoded_str);
    free(decoded_str);

    printf("All tests PASSED\n");
    return 0;
}