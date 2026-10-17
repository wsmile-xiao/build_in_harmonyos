#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <libdcadec/dca_context.h>
#include <libdcadec/dca_frame.h>
#include <libdcadec/dca_stream.h>

static int checks;

/*
 * First core frame from the official core_51_24_48_768_0.dtshd sample at
 * offset 0x74.  In a 16-bit big-endian core header the 14-bit frame-size
 * field starts at bit 46, so it spans header[5]..header[7] and is not byte
 * aligned.  Its stored value is 0x03ff; the DTS syntax adds one byte.
 */
static const uint8_t core_header[DCADEC_FRAME_HEADER_SIZE] = {
    0x7f, 0xfe, 0x80, 0x01, 0xfc, 0x3c, 0x3f, 0xf2,
    0x75, 0xe0, 0x05, 0x3b, 0x80, 0x09, 0x8c, 0x63
};

static size_t core_header_frame_size(const uint8_t *header)
{
    size_t stored_size = ((size_t)(header[5] & 0x03) << 12) |
                         ((size_t)header[6] << 4) |
                         ((size_t)header[7] >> 4);

    return stored_size + 1;
}

static int check(int condition, const char *message)
{
    ++checks;
    if (!condition) {
        fprintf(stderr, "check %d failed: %s\n", checks, message);
        return 0;
    }
    return 1;
}

int main(void)
{
    static const uint8_t invalid_header[DCADEC_FRAME_HEADER_SIZE] = {0};
    const size_t encoded_frame_size = core_header_frame_size(core_header);
    size_t frame_size = 0;
    struct dcadec_context *context;

    if (!check(dcadec_version() == DCADEC_API_VERSION, "runtime API version")) return 1;
    if (!check(DCADEC_API_VERSION_MAJOR == 0, "API major version")) return 1;
    if (!check(DCADEC_API_VERSION_MINOR == 1, "API minor version")) return 1;
    if (!check(strcmp(dcadec_strerror(0), "No error") == 0, "zero status text")) return 1;
    if (!check(strcmp(dcadec_strerror(-DCADEC_EINVAL), "Invalid argument") == 0,
               "error status text")) return 1;
    if (!check(strcmp(dcadec_strerror(DCADEC_WCOREAUXFAILED),
                      "Failed to parse core auxiliary data") == 0,
               "warning status text")) return 1;
    if (!check(dcadec_frame_parse_header(core_header, &frame_size) ==
               DCADEC_FRAME_TYPE_CORE, "DTS core header type")) return 1;
    if (!check(encoded_frame_size == 1024 && frame_size == encoded_frame_size,
               "DTS frame size")) return 1;
    if (!check(dcadec_frame_buffer_size(frame_size) ==
               frame_size + DCADEC_BUFFER_PADDING,
               "padded decoder buffer size")) return 1;
    if (!check(dcadec_frame_parse_header(invalid_header, &frame_size) ==
               -DCADEC_ENOSYNC, "invalid sync rejection")) return 1;
    context = dcadec_context_create(DCADEC_FLAG_STRICT);
    if (!check(context != NULL, "decoder context creation")) return 1;
    dcadec_context_destroy(context);
    if (!check(dcadec_stream_open("dcadec-file-that-does-not-exist.dtshd", 0) == NULL,
               "missing stream rejection")) return 1;

    printf("dcadec consumer API: %d/12 checks passed\n", checks);
    return 0;
}
