/*
 * test_msgpack.c — consumer-side serialization round-trip test for msgpack-c 7.0.1.
 *
 * Uses the real public C API confirmed from the 7.0.1 headers (object.h,
 * sbuffer.h, unpack.h): msgpack_sbuffer / msgpack_packer / msgpack_unpacked /
 * msgpack_object. Packs a mixed array [42, true, "msgpack"], unpacks it back as
 * ONE array object, and asserts each element via result.data.via.array.ptr[].
 * Only links against the Conan package's libmsgpack-c (no host install / source).
 */
#include <msgpack.h>
#include <stdio.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (!(cond)) {                                                         \
            fprintf(stderr, "FAIL: %s (line %d)\n", (msg), __LINE__);          \
            failures++;                                                        \
        } else {                                                               \
            printf("ok: %s\n", (msg));                                         \
        }                                                                      \
    } while (0)

int main(void)
{
    /* ---- pack: [42, true, "msgpack"] ---- */
    msgpack_sbuffer sbuf;
    msgpack_packer pk;
    msgpack_sbuffer_init(&sbuf);
    msgpack_packer_init(&pk, &sbuf, msgpack_sbuffer_write);

    CHECK(msgpack_pack_array(&pk, 3) == 0, "pack array header [3]");
    CHECK(msgpack_pack_int(&pk, 42) == 0, "pack int 42");
    CHECK(msgpack_pack_true(&pk) == 0, "pack true");
    CHECK(msgpack_pack_str(&pk, 7) == 0, "pack str header (len 7)");
    CHECK(msgpack_pack_str_body(&pk, "msgpack", 7) == 0, "pack str body");
    CHECK(sbuf.size > 0, "buffer has serialized bytes");

    /* ---- unpack the whole array back as a single object ---- */
    msgpack_unpacked result;
    msgpack_unpacked_init(&result);

    size_t off = 0;
    msgpack_unpack_return ret = msgpack_unpack_next(&result, sbuf.data, sbuf.size, &off);
    CHECK(ret == MSGPACK_UNPACK_SUCCESS, "unpack array object");

    if (ret != MSGPACK_UNPACK_SUCCESS) {
        fprintf(stderr, "msgpack_unpack_next failed: %d\n", (int)ret);
        msgpack_unpacked_destroy(&result);
        msgpack_sbuffer_destroy(&sbuf);
        return 1;
    }

    CHECK(result.data.type == MSGPACK_OBJECT_ARRAY, "top-level type is ARRAY");
    CHECK(result.data.via.array.size == 3, "array has 3 elements");

    /* element 0: 42 (positive integer) */
    msgpack_object e0 = result.data.via.array.ptr[0];
    CHECK(e0.type == MSGPACK_OBJECT_POSITIVE_INTEGER, "elem[0] type is int");
    CHECK(e0.via.u64 == 42, "elem[0] value == 42");

    /* element 1: true */
    msgpack_object e1 = result.data.via.array.ptr[1];
    CHECK(e1.type == MSGPACK_OBJECT_BOOLEAN, "elem[1] type is bool");
    CHECK(e1.via.boolean == true, "elem[1] value == true");

    /* element 2: "msgpack" (str) */
    msgpack_object e2 = result.data.via.array.ptr[2];
    CHECK(e2.type == MSGPACK_OBJECT_STR, "elem[2] type is str");
    CHECK(e2.via.str.size == 7, "elem[2] str length == 7");
    CHECK(strncmp(e2.via.str.ptr, "msgpack", 7) == 0, "elem[2] value == msgpack");

    /* the whole buffer must now be consumed */
    ret = msgpack_unpack_next(&result, sbuf.data, sbuf.size, &off);
    CHECK(ret == MSGPACK_UNPACK_CONTINUE, "buffer exhausted (CONTINUE)");

    /* ---- object equality API ---- */
    msgpack_object a, b;
    msgpack_object_init_signed_integer(&a, -123);
    msgpack_object_init_signed_integer(&b, -123);
    CHECK(msgpack_object_equal(a, b), "msgpack_object_equal for equal ints");

    msgpack_object_init_boolean(&b, false);
    CHECK(!msgpack_object_equal(a, b), "msgpack_object_equal for differing values");

    /* ---- object print API (smoke) ---- */
    char pbuf[128] = {0};
    int written = msgpack_object_print_buffer(pbuf, sizeof(pbuf), a);
    CHECK(written > 0, "msgpack_object_print_buffer returns positive");

    msgpack_unpacked_destroy(&result);
    msgpack_sbuffer_destroy(&sbuf);

    if (failures > 0) {
        fprintf(stderr, "\n%d assertion(s) failed\n", failures);
        return 1;
    }
    printf("\nall msgpack round-trip assertions passed\n");
    return 0;
}
