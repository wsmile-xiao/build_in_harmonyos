#include <tinyframe/tinyframe.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define CHECK(expr) do { if (!(expr)) { \
    fprintf(stderr, "check failed at line %d: %s\n", __LINE__, #expr); \
    return 1; } } while (0)

static uint32_t read_be32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}

static int test_frame_size(void)
{
    CHECK(tinyframe_frame_size(0) == 4);
    CHECK(tinyframe_frame_size(127) == 131);
    return 0;
}

static int test_header_endian(void)
{
    uint8_t out[4];
    tinyframe_set_header(out, 0x01020304U);
    CHECK(out[0] == 1 && out[1] == 2 && out[2] == 3 && out[3] == 4);
    return 0;
}

static int write_control(uint32_t type, uint8_t *out, size_t size,
                         struct tinyframe_writer *writer)
{
    CHECK(tinyframe_write_control(writer, out, size, type, NULL, 0) == tinyframe_ok);
    CHECK(writer->bytes_wrote == 12);
    CHECK(read_be32(out) == 0 && read_be32(out + 8) == type);
    return 0;
}

static int test_ready_control(void)
{
    uint8_t out[32];
    struct tinyframe_writer writer = TINYFRAME_WRITER_INITIALIZER;
    return write_control(TINYFRAME_CONTROL_READY, out, sizeof(out), &writer);
}

static int test_start_control(void)
{
    uint8_t out[64];
    struct tinyframe_writer writer = TINYFRAME_WRITER_INITIALIZER;
    CHECK(tinyframe_write_control_start(&writer, out, sizeof(out), "dns", 3) == tinyframe_ok);
    CHECK(writer.bytes_wrote == 23);
    CHECK(read_be32(out + 8) == TINYFRAME_CONTROL_START);
    CHECK(read_be32(out + 12) == TINYFRAME_CONTROL_FIELD_CONTENT_TYPE);
    CHECK(read_be32(out + 16) == 3 && memcmp(out + 20, "dns", 3) == 0);
    return 0;
}

static int test_frame_roundtrip(void)
{
    static const uint8_t payload[] = {0, 1, 2, 0xfe, 0xff};
    uint8_t control[32], frame[32];
    struct tinyframe_writer writer = TINYFRAME_WRITER_INITIALIZER;
    struct tinyframe_reader reader = TINYFRAME_READER_INITIALIZER;
    CHECK(write_control(TINYFRAME_CONTROL_READY, control, sizeof(control), &writer) == 0);
    CHECK(tinyframe_read(&reader, control, writer.bytes_wrote) == tinyframe_have_control);
    CHECK(tinyframe_write_frame(&writer, frame, sizeof(frame), payload, sizeof(payload)) == tinyframe_ok);
    CHECK(tinyframe_read(&reader, frame, writer.bytes_wrote) == tinyframe_have_frame);
    CHECK(reader.frame.length == sizeof(payload));
    CHECK(memcmp(reader.frame.data, payload, sizeof(payload)) == 0);
    return 0;
}

static int test_terminal(uint32_t type, enum tinyframe_result expected)
{
    uint8_t out[32];
    struct tinyframe_writer writer = TINYFRAME_WRITER_INITIALIZER;
    struct tinyframe_reader reader = TINYFRAME_READER_INITIALIZER;
    CHECK(write_control(type, out, sizeof(out), &writer) == 0);
    CHECK(tinyframe_read(&reader, out, writer.bytes_wrote) == expected);
    CHECK(reader.state == tinyframe_done);
    return 0;
}

static int test_partial_input(void)
{
    uint8_t out[32];
    struct tinyframe_writer writer = TINYFRAME_WRITER_INITIALIZER;
    struct tinyframe_reader reader = TINYFRAME_READER_INITIALIZER;
    CHECK(write_control(TINYFRAME_CONTROL_READY, out, sizeof(out), &writer) == 0);
    CHECK(tinyframe_read(&reader, out, 11) == tinyframe_need_more);
    CHECK(reader.state == tinyframe_control);
    return 0;
}

static int test_invalid_field(void)
{
    uint8_t out[64];
    static const uint8_t value[] = "x";
    struct tinyframe_writer writer = TINYFRAME_WRITER_INITIALIZER;
    struct tinyframe_control_field field = {99, 1, value};
    CHECK(tinyframe_write_control(&writer, out, sizeof(out),
                                  TINYFRAME_CONTROL_READY, &field, 1) == tinyframe_error);
    return 0;
}

int main(int argc, char **argv)
{
    CHECK(argc == 2);
    if (!strcmp(argv[1], "frame_size")) return test_frame_size();
    if (!strcmp(argv[1], "header_endian")) return test_header_endian();
    if (!strcmp(argv[1], "ready_control")) return test_ready_control();
    if (!strcmp(argv[1], "start_control")) return test_start_control();
    if (!strcmp(argv[1], "frame_roundtrip")) return test_frame_roundtrip();
    if (!strcmp(argv[1], "stop_control")) return test_terminal(TINYFRAME_CONTROL_STOP, tinyframe_stopped);
    if (!strcmp(argv[1], "finish_control")) return test_terminal(TINYFRAME_CONTROL_FINISH, tinyframe_finished);
    if (!strcmp(argv[1], "partial_input")) return test_partial_input();
    if (!strcmp(argv[1], "invalid_field")) return test_invalid_field();
    fprintf(stderr, "unknown case: %s\n", argv[1]);
    return 2;
}
