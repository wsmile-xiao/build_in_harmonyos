#include <pb.h>
#include <pb_decode.h>
#include <pb_encode.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int fail(const char *message)
{
    fprintf(stderr, "%s\n", message);
    return 1;
}

int main(void)
{
    uint8_t buffer[32] = {0};
    pb_ostream_t out = pb_ostream_from_buffer(buffer, sizeof(buffer));

    if (!pb_encode_tag(&out, PB_WT_VARINT, 1))
        return fail("failed to encode field 1 tag");
    if (!pb_encode_varint(&out, 150))
        return fail("failed to encode field 1 varint");
    if (!pb_encode_tag(&out, PB_WT_STRING, 2))
        return fail("failed to encode field 2 tag");
    if (!pb_encode_string(&out, (const pb_byte_t *)"OHOS", 4))
        return fail("failed to encode field 2 string");

    pb_istream_t in = pb_istream_from_buffer(buffer, out.bytes_written);
    pb_wire_type_t wire_type = (pb_wire_type_t)0;
    uint32_t tag = 0;
    bool eof = false;
    uint64_t value = 0;
    uint8_t text[4] = {0};

    if (!pb_decode_tag(&in, &wire_type, &tag, &eof) || eof)
        return fail("failed to decode field 1 tag");
    if (tag != 1 || wire_type != PB_WT_VARINT)
        return fail("unexpected field 1 tag");
    if (!pb_decode_varint(&in, &value) || value != 150)
        return fail("unexpected field 1 value");

    if (!pb_decode_tag(&in, &wire_type, &tag, &eof) || eof)
        return fail("failed to decode field 2 tag");
    if (tag != 2 || wire_type != PB_WT_STRING)
        return fail("unexpected field 2 tag");
    /* pb_encode_string writes a varint length prefix before the bytes;
       decode it first, then read exactly that many bytes. */
    uint64_t string_len = 0;
    if (!pb_decode_varint(&in, &string_len) || string_len != sizeof(text))
        return fail("unexpected field 2 string length");
    if (!pb_read(&in, text, sizeof(text)) || memcmp(text, "OHOS", sizeof(text)) != 0)
        return fail("unexpected field 2 payload");

    if (in.bytes_left != 0)
        return fail("decoder did not consume the whole buffer");

    puts("nanopb wire encode/decode roundtrip passed");
    return 0;
}
