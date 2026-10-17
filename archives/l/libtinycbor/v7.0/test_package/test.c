#include <stdio.h>
#include <string.h>
#include <tinycbor/cbor.h>

int main(void) {
    uint8_t buf[64];
    CborEncoder encoder;
    CborError err;

    /* Encode an integer */
    cbor_encoder_init(&encoder, buf, sizeof(buf), 0);
    err = cbor_encode_int(&encoder, 42);
    if (err != CborNoError) {
        printf("FAIL: encode error: %s\n", cbor_error_string(err));
        return 1;
    }

    /* Decode and verify */
    CborParser parser;
    CborValue value;
    size_t encoded_len = (size_t)(encoder.data.ptr - buf);
    err = cbor_parser_init(buf, encoded_len, 0, &parser, &value);
    if (err != CborNoError) {
        printf("FAIL: parse error: %s\n", cbor_error_string(err));
        return 1;
    }

    int val = 0;
    err = cbor_value_get_int(&value, &val);
    if (err != CborNoError) {
        printf("FAIL: get_int error: %s\n", cbor_error_string(err));
        return 1;
    }

    if (val != 42) {
        printf("FAIL: expected 42, got %d\n", val);
        return 1;
    }

    printf("tinycbor test PASSED: encode/decode int 42 OK\n");
    return 0;
}
