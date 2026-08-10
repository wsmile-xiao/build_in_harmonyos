#include <stdio.h>
#include <string.h>
#include <msgpack.h>

int main(void) {
    /* Pack an array [1, true, "example"] using msgpack-c API */
    msgpack_sbuffer sbuf;
    msgpack_sbuffer_init(&sbuf);

    msgpack_packer pk;
    msgpack_packer_init(&pk, &sbuf, msgpack_sbuffer_write);

    msgpack_pack_array(&pk, 3);
    msgpack_pack_int(&pk, 1);
    msgpack_pack_true(&pk);
    msgpack_pack_str(&pk, 7);
    msgpack_pack_str_body(&pk, "example", 7);

    /* Unpack and verify */
    msgpack_unpacked result;
    msgpack_unpacked_init(&result);

    size_t offset = 0;
    bool ok = msgpack_unpack_next(&result, sbuf.data, sbuf.size, &offset);
    if (!ok) {
        fprintf(stderr, "FAIL: msgpack_unpack_next returned false\n");
        msgpack_sbuffer_destroy(&sbuf);
        msgpack_unpacked_destroy(&result);
        return 1;
    }

    if (result.data.type != MSGPACK_OBJECT_ARRAY) {
        fprintf(stderr, "FAIL: expected ARRAY, got %d\n", result.data.type);
        msgpack_sbuffer_destroy(&sbuf);
        msgpack_unpacked_destroy(&result);
        return 1;
    }

    if (result.data.via.array.size != 3) {
        fprintf(stderr, "FAIL: expected array size 3, got %u\n", result.data.via.array.size);
        msgpack_sbuffer_destroy(&sbuf);
        msgpack_unpacked_destroy(&result);
        return 1;
    }

    msgpack_object *arr = result.data.via.array.ptr;
    if (arr[0].via.i64 != 1) {
        fprintf(stderr, "FAIL: expected arr[0]=1, got %lld\n", arr[0].via.i64);
        msgpack_sbuffer_destroy(&sbuf);
        msgpack_unpacked_destroy(&result);
        return 1;
    }
    if (arr[1].via.boolean != true) {
        fprintf(stderr, "FAIL: expected arr[1]=true\n");
        msgpack_sbuffer_destroy(&sbuf);
        msgpack_unpacked_destroy(&result);
        return 1;
    }
    if (arr[2].via.str.size != 7 || strncmp(arr[2].via.str.ptr, "example", 7) != 0) {
        fprintf(stderr, "FAIL: expected arr[2]=\"example\"\n");
        msgpack_sbuffer_destroy(&sbuf);
        msgpack_unpacked_destroy(&result);
        return 1;
    }

    printf("test msgpack-c 7.0.0: pack/unpack [1, true, \"example\"] OK\n");

    msgpack_sbuffer_destroy(&sbuf);
    msgpack_unpacked_destroy(&result);
    return 0;
}
