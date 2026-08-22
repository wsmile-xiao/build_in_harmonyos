/* Consumer test for cb0r 1.0.0 — exercises core CBOR parse and write API.
 *
 * Covers: integer, negative, byte string, UTF-8 string, array, map,
 *         and the cb0r_write helper.  All assertions are real API checks,
 *         not mere "hello world" prints.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include "cb0r.h"

#define ASSERT(cond, msg)                                              \
    do {                                                               \
        if (!(cond)) {                                                 \
            fprintf(stderr, "FAIL line %d: %s\n", __LINE__, (msg));   \
            exit(1);                                                   \
        }                                                              \
    } while (0)

/* ---- helper: hex digit -> 4-bit value ---- */
static uint8_t hexval(char x)
{
    if (x >= '0' && x <= '9') return (uint8_t)(x - '0');
    if (x >= 'a' && x <= 'f') return (uint8_t)(x - 'a' + 10);
    if (x >= 'A' && x <= 'F') return (uint8_t)(x - 'A' + 10);
    return 0;
}

/* ---- helper: hex string -> byte buffer ---- */
static uint32_t unhex(const char *in, uint8_t *out)
{
    uint32_t j;
    uint8_t *c = out;
    if (!out || !in) return 0;
    uint32_t len = (uint32_t)strlen(in);
    for (j = 0; (j + 1) < len; j += 2) {
        *c = (uint8_t)((hexval(in[j]) << 4) | hexval(in[j + 1]));
        c++;
    }
    return len / 2;
}

int main(void)
{
    struct cb0r_s res_s = {0};
    cb0r_t res = &res_s;
    uint8_t buf[256] = {0};
    uint8_t *end = NULL;
    uint32_t len;

    /* --- Test 1: unsigned int 1 --- */
    len = unhex("01", buf);
    end = cb0r(buf, buf + len, 0, res);
    ASSERT(end == buf + len, "uint 1: end mismatch");
    ASSERT(res->type == CB0R_INT, "uint 1: wrong type");
    ASSERT(res->value == 1, "uint 1: wrong value");

    /* --- Test 2: unsigned int 256 (2-byte) --- */
    len = unhex("190100", buf);
    end = cb0r(buf, buf + len, 0, res);
    ASSERT(end == buf + len, "uint 256: end mismatch");
    ASSERT(res->type == CB0R_INT, "uint 256: wrong type");
    ASSERT(res->value == 256, "uint 256: wrong value");

    /* --- Test 3: negative int -1 (CBOR 0x20) --- */
    len = unhex("20", buf);
    end = cb0r(buf, buf + len, 0, res);
    ASSERT(end == buf + len, "neg -1: end mismatch");
    ASSERT(res->type == CB0R_NEG, "neg -1: wrong type");
    /* res->value is the unsigned magnitude; -1 - magnitude == actual value */
    ASSERT(-1 - (int64_t)res->value == -1, "neg -1: wrong value");

    /* --- Test 4: byte string "hello" --- */
    len = unhex("4568656c6c6f", buf);
    end = cb0r(buf, buf + len, 0, res);
    ASSERT(end == buf + len, "bytes hello: end mismatch");
    ASSERT(res->type == CB0R_BYTE, "bytes hello: wrong type");
    ASSERT(res->length == 5, "bytes hello: wrong length");
    ASSERT(memcmp(res->start + res->header, "hello", 5) == 0,
           "bytes hello: content mismatch");

    /* --- Test 5: UTF-8 string "a" --- */
    len = unhex("6161", buf);
    end = cb0r(buf, buf + len, 0, res);
    ASSERT(end == buf + len, "utf8 a: end mismatch");
    ASSERT(res->type == CB0R_UTF8, "utf8 a: wrong type");
    ASSERT(res->length == 1, "utf8 a: wrong length");

    /* --- Test 6: empty array --- */
    len = unhex("80", buf);
    end = cb0r(buf, buf + len, 0, res);
    ASSERT(end == buf + len, "empty array: end mismatch");
    ASSERT(res->type == CB0R_ARRAY, "empty array: wrong type");
    ASSERT(res->count == 0, "empty array: wrong count");

    /* --- Test 7: array [1, 2] --- */
    len = unhex("820102", buf);
    end = cb0r(buf, buf + len, 0, res);
    ASSERT(end == buf + len, "array [1,2]: end mismatch");
    ASSERT(res->type == CB0R_ARRAY, "array [1,2]: wrong type");
    ASSERT(res->count == 2, "array [1,2]: wrong count");

    /* --- Test 8: map {"a": 0} --- */
    len = unhex("a1616100", buf);
    end = cb0r(buf, buf + len, 0, res);
    ASSERT(end == buf + len, "map {a:0}: end mismatch");
    ASSERT(res->type == CB0R_MAP, "map {a:0}: wrong type");
    ASSERT(res->count == 2, "map {a:0}: wrong count (key+value)");

    /* --- Test 9: cb0r_read wrapper --- */
    len = unhex("1818", buf);  /* unsigned 24 */
    ASSERT(cb0r_read(buf, len, res), "cb0r_read: returned false");
    ASSERT(res->type == CB0R_INT, "cb0r_read: wrong type");
    ASSERT(res->value == 24, "cb0r_read: wrong value");

    /* --- Test 10: cb0r_get on array --- */
    len = unhex("83010203", buf);  /* [1, 2, 3] */
    end = cb0r(buf, buf + len, 0, res);
    ASSERT(res->type == CB0R_ARRAY && res->count == 3, "get: parse array");
    struct cb0r_s elem_s = {0};
    cb0r_t elem = &elem_s;
    ASSERT(cb0r_get(res, 1, elem), "cb0r_get index 1: failed");
    ASSERT(elem->type == CB0R_INT && elem->value == 2,
           "cb0r_get index 1: wrong value");

    /* --- Test 11: cb0r_write helper --- */
    uint8_t out[16] = {0};
    uint8_t wlen = cb0r_write(out, CB0R_INT, 42);
    ASSERT(wlen > 0, "cb0r_write: returned 0");
    end = cb0r(out, out + wlen, 0, res);
    ASSERT(end == out + wlen, "cb0r_write round-trip: end mismatch");
    ASSERT(res->type == CB0R_INT, "cb0r_write round-trip: wrong type");
    ASSERT(res->value == 42, "cb0r_write round-trip: wrong value");

    /* --- Test 12: cb0r_find on map --- */
    len = unhex("a20102616103", buf);  /* {1: 2, "a": 3} */
    end = cb0r(buf, buf + len, 0, res);
    ASSERT(res->type == CB0R_MAP, "find: not a map");
    struct cb0r_s val_s = {0};
    cb0r_t val = &val_s;
    ASSERT(cb0r_find(res, CB0R_INT, 1, NULL, val), "cb0r_find key 1: failed");
    ASSERT(val->type == CB0R_INT && val->value == 2,
           "cb0r_find key 1: wrong value");

    printf("test cb0r 1.0.0: PASS\n");
    return 0;
}
