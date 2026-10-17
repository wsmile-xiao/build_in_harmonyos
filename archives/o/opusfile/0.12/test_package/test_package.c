#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <ogg/ogg.h>
#include <opus/opus.h>
#include <opus/opusfile.h>

struct byte_buffer {
    unsigned char *data;
    size_t size;
    size_t capacity;
};

static void fail(const char *message)
{
    fprintf(stderr, "FAIL opusfile consumer: %s\n", message);
    exit(1);
}

static void append_bytes(struct byte_buffer *buffer,
                         const unsigned char *data,
                         size_t size)
{
    size_t required;
    size_t capacity;
    unsigned char *grown;

    if (size > SIZE_MAX - buffer->size) {
        fail("buffer size overflow");
    }
    required = buffer->size + size;
    if (required > buffer->capacity) {
        capacity = buffer->capacity == 0 ? 4096 : buffer->capacity;
        while (capacity < required) {
            if (capacity > SIZE_MAX / 2) {
                capacity = required;
                break;
            }
            capacity *= 2;
        }
        grown = (unsigned char *)realloc(buffer->data, capacity);
        if (grown == NULL) {
            fail("out of memory");
        }
        buffer->data = grown;
        buffer->capacity = capacity;
    }
    memcpy(buffer->data + buffer->size, data, size);
    buffer->size = required;
}

static void append_page(struct byte_buffer *buffer, const ogg_page *page)
{
    append_bytes(buffer, page->header, (size_t)page->header_len);
    append_bytes(buffer, page->body, (size_t)page->body_len);
}

static void flush_pages(ogg_stream_state *stream, struct byte_buffer *buffer)
{
    ogg_page page;

    while (ogg_stream_flush(stream, &page) != 0) {
        append_page(buffer, &page);
    }
}

static void write_u32le(unsigned char *destination, uint32_t value)
{
    destination[0] = (unsigned char)(value & 0xffU);
    destination[1] = (unsigned char)((value >> 8) & 0xffU);
    destination[2] = (unsigned char)((value >> 16) & 0xffU);
    destination[3] = (unsigned char)((value >> 24) & 0xffU);
}

static void make_test_stream(struct byte_buffer *buffer)
{
    ogg_stream_state stream;
    ogg_packet packet;
    OpusEncoder *encoder;
    opus_int16 input[960];
    unsigned char encoded[4096];
    unsigned char head[19];
    unsigned char tags[20];
    int error;
    int encoded_size;

    if (ogg_stream_init(&stream, 0x4f505553) != 0) {
        fail("ogg_stream_init failed");
    }

    memset(head, 0, sizeof(head));
    memcpy(head, "OpusHead", 8);
    head[8] = 1;
    head[9] = 1;
    write_u32le(head + 12, 48000U);

    memset(&packet, 0, sizeof(packet));
    packet.packet = head;
    packet.bytes = (long)sizeof(head);
    packet.b_o_s = 1;
    packet.packetno = 0;
    if (ogg_stream_packetin(&stream, &packet) != 0) {
        fail("OpusHead packet rejected");
    }
    flush_pages(&stream, buffer);

    memset(tags, 0, sizeof(tags));
    memcpy(tags, "OpusTags", 8);
    write_u32le(tags + 8, 4U);
    memcpy(tags + 12, "test", 4);
    write_u32le(tags + 16, 0U);

    memset(&packet, 0, sizeof(packet));
    packet.packet = tags;
    packet.bytes = (long)sizeof(tags);
    packet.packetno = 1;
    if (ogg_stream_packetin(&stream, &packet) != 0) {
        fail("OpusTags packet rejected");
    }
    flush_pages(&stream, buffer);

    encoder = opus_encoder_create(48000, 1, OPUS_APPLICATION_AUDIO, &error);
    if (encoder == NULL || error != OPUS_OK) {
        fail("opus_encoder_create failed");
    }
    memset(input, 0, sizeof(input));
    encoded_size = opus_encode(encoder, input, 960, encoded, (opus_int32)sizeof(encoded));
    opus_encoder_destroy(encoder);
    if (encoded_size <= 0) {
        fail("opus_encode failed");
    }

    memset(&packet, 0, sizeof(packet));
    packet.packet = encoded;
    packet.bytes = encoded_size;
    packet.e_o_s = 1;
    packet.granulepos = 960;
    packet.packetno = 2;
    if (ogg_stream_packetin(&stream, &packet) != 0) {
        fail("audio packet rejected");
    }
    flush_pages(&stream, buffer);
    ogg_stream_clear(&stream);
}

static int decode_all(OggOpusFile *file)
{
    opus_int16 output[1920];
    int total = 0;

    for (;;) {
        int link = -1;
        int decoded = op_read(file, output, 1920, &link);
        if (decoded == 0) {
            break;
        }
        if (decoded < 0) {
            fail("op_read failed");
        }
        if (link != 0) {
            fail("unexpected link index");
        }
        total += decoded;
    }
    return total;
}

static int decode_memory(const struct byte_buffer *buffer)
{
    OggOpusFile *file;
    const OpusHead *head;
    int error = 0;
    int total;

    file = op_open_memory(buffer->data, buffer->size, &error);
    if (file == NULL || error != 0) {
        fail("op_open_memory failed");
    }
    head = op_head(file, -1);
    if (head == NULL || head->channel_count != 1 || head->input_sample_rate != 48000U) {
        fail("decoded OpusHead mismatch");
    }
    if (op_pcm_total(file, -1) != 960) {
        fail("memory PCM total mismatch");
    }
    total = decode_all(file);
    op_free(file);
    return total;
}

static int decode_file_url(const struct byte_buffer *buffer)
{
    static const char filename[] = "opusfile-consumer.opus";
    char directory[4096];
    char url[8192];
    OggOpusFile *file;
    FILE *output;
    int error = 0;
    int total;
    int length;

    output = fopen(filename, "wb");
    if (output == NULL) {
        fail("fixture file open failed");
    }
    if (fwrite(buffer->data, 1, buffer->size, output) != buffer->size ||
        fclose(output) != 0) {
        fail("fixture file write failed");
    }
    if (getcwd(directory, sizeof(directory)) == NULL) {
        fail("getcwd failed");
    }
    length = snprintf(url, sizeof(url), "file://%s/%s", directory, filename);
    if (length < 0 || (size_t)length >= sizeof(url)) {
        fail("file URL overflow");
    }
    file = op_open_url(url, &error, NULL);
    if (file == NULL || error != 0) {
        fail("op_open_url(file:) failed");
    }
    total = decode_all(file);
    op_free(file);
    if (remove(filename) != 0) {
        fprintf(stderr, "cleanup failed: %s\n", strerror(errno));
        return -1;
    }
    return total;
}

int main(void)
{
    struct byte_buffer stream = {0};
    int memory_samples;
    int file_samples;

    make_test_stream(&stream);
    memory_samples = decode_memory(&stream);
    file_samples = decode_file_url(&stream);
    free(stream.data);

    if (memory_samples != 960 || file_samples != 960) {
        fail("decoded sample count mismatch");
    }
    printf("PASS opusfile consumer memory_samples=%d file_samples=%d\n",
           memory_samples, file_samples);
    return 0;
}
