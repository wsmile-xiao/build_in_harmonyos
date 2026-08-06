#include <X11/ICE/ICElib.h>
#include <X11/ICE/ICEutil.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(condition, message, code) \
    do { \
        if (!(condition)) { \
            fprintf(stderr, "%s\n", (message)); \
            result = (code); \
            goto cleanup; \
        } \
    } while (0)

int main(void) {
    static const char path[] = "libice-auth-roundtrip.bin";
    static char protocol_name[] = "ICE";
    static char protocol_data[] = "protocol-data";
    static char network_id[] = "local/test";
    static char auth_name[] = "MIT-MAGIC-COOKIE-1";
    static char auth_data[] = {0x00, 0x11, 0x22, 0x33, 0x44, 0x55};
    IceAuthFileEntry input = {
        protocol_name,
        (unsigned short)(sizeof(protocol_data) - 1),
        protocol_data,
        network_id,
        auth_name,
        (unsigned short)sizeof(auth_data),
        auth_data,
    };
    IceAuthFileEntry *output = NULL;
    FILE *stream = NULL;
    int result = 0;

    (void)remove(path);
    stream = fopen(path, "w+b");
    CHECK(stream != NULL, "cannot create authority round-trip file", 1);
    CHECK(IceWriteAuthFileEntry(stream, &input) != 0,
          "IceWriteAuthFileEntry failed", 2);
    CHECK(fflush(stream) == 0, "cannot flush authority file", 3);
    CHECK(fseek(stream, 0L, SEEK_SET) == 0, "cannot rewind authority file", 4);

    output = IceReadAuthFileEntry(stream);
    CHECK(output != NULL, "IceReadAuthFileEntry failed", 5);
    CHECK(strcmp(output->protocol_name, input.protocol_name) == 0,
          "protocol name mismatch", 6);
    CHECK(output->protocol_data_length == input.protocol_data_length &&
              memcmp(output->protocol_data, input.protocol_data,
                     input.protocol_data_length) == 0,
          "protocol data mismatch", 7);
    CHECK(strcmp(output->network_id, input.network_id) == 0,
          "network id mismatch", 8);
    CHECK(strcmp(output->auth_name, input.auth_name) == 0,
          "authentication name mismatch", 9);
    CHECK(output->auth_data_length == input.auth_data_length &&
              memcmp(output->auth_data, input.auth_data,
                     input.auth_data_length) == 0,
          "authentication data mismatch", 10);
    CHECK(IceReadAuthFileEntry(stream) == NULL,
          "authority reader did not stop at EOF", 11);

cleanup:
    IceFreeAuthFileEntry(output);
    if (stream != NULL && fclose(stream) != 0 && result == 0) {
        fprintf(stderr, "cannot close authority file\n");
        result = 12;
    }
    if (remove(path) != 0 && result == 0) {
        fprintf(stderr, "cannot remove authority file\n");
        result = 13;
    }
    if (result == 0) {
        puts("LIBICE_TEST auth_roundtrip PASS");
    }
    return result;
}
