/*
 * test_aribb24.c — L1 consumer test for the aribb24 package.
 *
 * Exercises the real ARIB STD-B24 pipeline on the device:
 *   1. instance lifecycle (arib_instance_new / arib_instance_destroy)
 *   2. lazy parser/decoder creation (arib_get_parser / arib_get_decoder)
 *   3. caption PES parsing (arib_parse_pes) of a management data group and
 *      of a statement data group carrying one caption data unit
 *   4. subtitle data extraction (arib_parser_get_data) with byte-exact check
 *   5. JIS character decoding (arib_initialize_decoder_a_profile +
 *      arib_decode_buffer)
 *
 * Packet layout follows ARIB STD-B24 Volume 3 Chapter 5 (Independent PES
 * transmission protocol): data_group_id byte (0x80 management / 0x81
 * statement), private_stream_id 0xFF, reserved + PES header length, then
 * the data group (6-bit data_group_id + version, link, last link, size)
 * and the caption data units.
 */
#include <stdio.h>
#include <string.h>

#include <aribb24/aribb24.h>
#include <aribb24/parser.h>
#include <aribb24/decoder.h>

static int g_failures = 0;

#define CHECK(cond, msg)                                     \
    do {                                                     \
        if (cond) {                                          \
            printf("[ok]   %s\n", msg);                      \
        } else {                                             \
            printf("[fail] %s\n", msg);                      \
            g_failures++;                                    \
        }                                                    \
    } while (0)

/* Caption MANAGEMENT data group (data_group_id 0x80) with no PES private
 * data and no data units: TMD=0, num_languages=0, loop length 0. */
static const unsigned char caption_mgmt[] = {
    0x80, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};

/* Caption STATEMENT data group (data_group_id 0x81) carrying one caption
 * data unit (unit separator 0x1F, data_unit_parameter 0x20 = statement
 * body, size 1) with a single byte 'A'.  The inner 6-bit data_group_id is
 * 0x01 so the parser takes the statement branch (0x00/0x20 map to
 * management). */
static const unsigned char caption_stmt[] = {
    0x81, 0xFF, 0x00,
    0x04, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x06,
    0x1F, 0x20, 0x00, 0x00, 0x01, 0x41
};

int main(void)
{
    arib_instance_t *instance = arib_instance_new(NULL);
    CHECK(instance != NULL, "arib_instance_new() creates an instance");

    arib_parser_t *parser = arib_get_parser(instance);
    CHECK(parser != NULL, "arib_get_parser() creates a parser");

    arib_decoder_t *decoder = arib_get_decoder(instance);
    CHECK(decoder != NULL, "arib_get_decoder() creates a decoder");

    /* Management data group parses cleanly and yields no subtitle data. */
    arib_parse_pes(parser, caption_mgmt, sizeof(caption_mgmt));
    size_t mgmt_size = 1;
    const unsigned char *mgmt_data = arib_parser_get_data(parser, &mgmt_size);
    CHECK(mgmt_data == NULL && mgmt_size == 0,
          "management data group yields no subtitle data");

    /* Statement data group yields the caption data unit payload. */
    arib_parse_pes(parser, caption_stmt, sizeof(caption_stmt));
    size_t stmt_size = 0;
    const unsigned char *stmt_data = arib_parser_get_data(parser, &stmt_size);
    CHECK(stmt_data != NULL && stmt_size == 1,
          "statement data group yields 1 subtitle byte");
    CHECK(stmt_size == 1 && stmt_data[0] == 'A',
          "subtitle byte matches the injected caption data");

    /* Decode the extracted caption data (JIS -> UTF-8). */
    arib_initialize_decoder_a_profile(decoder);
    char ubuf[256];
    size_t decoded = arib_decode_buffer(decoder, stmt_data, stmt_size,
                                        ubuf, sizeof(ubuf));
    CHECK(decoded <= sizeof(ubuf),
          "arib_decode_buffer() returns in-bounds decoded size");

    (void) arib_decoder_get_time(decoder);
    (void) arib_decoder_get_regions(decoder);

    arib_instance_destroy(instance);
    CHECK(g_failures == 0, "all aribb24 API checks passed");
    return g_failures == 0 ? 0 : 1;
}
