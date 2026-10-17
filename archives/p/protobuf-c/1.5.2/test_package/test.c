#include <protobuf-c/protobuf-c.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* Verify library version string is accessible */
    const char *version = protobuf_c_version();
    if (!version || strlen(version) == 0) {
        fprintf(stderr, "FAIL: protobuf_c_version() returned null or empty\n");
        return 1;
    }
    printf("protobuf-c version: %s\n", version);

    /* Verify version number is non-zero */
    unsigned version_number = protobuf_c_version_number();
    if (version_number == 0) {
        fprintf(stderr, "FAIL: protobuf_c_version_number() returned 0\n");
        return 1;
    }
    printf("protobuf-c version number: %u\n", version_number);

    /* Verify ProtobufCBufferSimple can be initialized and used */
    uint8_t pad[128];
    ProtobufCBufferSimple simple = PROTOBUF_C_BUFFER_SIMPLE_INIT(pad);
    ProtobufCBuffer *buffer = (ProtobufCBuffer *)&simple;
    if (!buffer || !buffer->append) {
        fprintf(stderr, "FAIL: ProtobufCBufferSimple init failed\n");
        return 1;
    }
    printf("ProtobufCBufferSimple: initialized OK\n");

    printf("test protobuf-c: OK\n");
    return 0;
}
