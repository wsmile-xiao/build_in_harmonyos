/* Deterministic libopusenc consumer: encodes PCM to Ogg Opus and validates
 * the output structure (OggS capture, OpusHead, OpusTags, page count). */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <opus/opus.h>
#include <opusenc.h>

#define SAMPLE_RATE 48000
#define CHANNELS 2
#define FRAME_SIZE 960
#define FRAMES 4

static void fail(const char *message)
{
    fprintf(stderr, "FAIL libopusenc consumer: %s\n", message);
    exit(1);
}

/* Deterministic PCM: simple integer pattern, no RNG. */
static void fill_pcm(opus_int16 *pcm, int frame_index)
{
    int i;
    int j;
    for (i = 0; i < FRAME_SIZE; i++) {
        for (j = 0; j < CHANNELS; j++) {
            int v = ((i + frame_index * FRAME_SIZE + j * 7) % 256) - 128;
            pcm[i * CHANNELS + j] = (opus_int16)(v * 64);
        }
    }
}

static long read_entire_file(const char *path, unsigned char **out)
{
    FILE *f = fopen(path, "rb");
    long size;
    if (f == NULL) {
        fail("open encoded file failed");
    }
    if (fseek(f, 0, SEEK_END) != 0) {
        fail("seek encoded file failed");
    }
    size = ftell(f);
    if (size <= 0) {
        fail("encoded file is empty");
    }
    rewind(f);
    *out = (unsigned char *)malloc((size_t)size);
    if (*out == NULL) {
        fail("out of memory");
    }
    if (fread(*out, 1, (size_t)size, f) != (size_t)size) {
        fail("read encoded file failed");
    }
    fclose(f);
    return size;
}

static void check_ogg_structure(const unsigned char *data, long size)
{
    long pos = 0;
    int pages = 0;
    int saw_opushead = 0;
    int saw_opustags = 0;
    int saw_eos = 0;
    long payload = 0;

    while (pos < size) {
        unsigned int header_size;
        unsigned int body_size;
        unsigned int seg_count;
        unsigned int header_type;
        unsigned int i;
        const unsigned char *header;
        const unsigned char *seg_table;

        if (pos + 27 > size) {
            fail("truncated Ogg page header");
        }
        header = data + pos;
        if (memcmp(header, "OggS", 4) != 0) {
            fail("missing OggS capture pattern");
        }
        if (header[4] != 0) {
            fail("unsupported Ogg version");
        }
        header_type = header[5];
        seg_count = header[26];
        if (pos + 27 + seg_count > size) {
            fail("truncated Ogg segment table");
        }
        seg_table = header + 27;
        body_size = 0;
        for (i = 0; i < seg_count; i++) {
            body_size += seg_table[i];
        }
        header_size = 27u + seg_count;
        if (pos + (long)header_size + (long)body_size > size) {
            fail("truncated Ogg page body");
        }

        /* First page must start with OpusHead. */
        if (pages == 0) {
            if (body_size < 19 || memcmp(data + pos + header_size, "OpusHead", 8) != 0) {
                fail("first page is not OpusHead");
            }
            saw_opushead = 1;
        }
        /* Second page must start with OpusTags. */
        if (pages == 1) {
            if (body_size < 8 || memcmp(data + pos + header_size, "OpusTags", 8) != 0) {
                fail("second page is not OpusTags");
            }
            saw_opustags = 1;
        }
        if (header_type & 0x04) {
            saw_eos = 1;
        }
        payload += body_size;
        pages++;
        pos += (long)(header_size + body_size);
    }

    if (pages < 3) {
        fail("expected at least 3 Ogg pages");
    }
    if (!saw_opushead || !saw_opustags || !saw_eos) {
        fail("missing OpusHead/OpusTags/EOS in stream");
    }
    printf("INFO pages=%d payload=%ld\n", pages, payload);
}

int main(void)
{
    OggOpusEnc *enc;
    OggOpusComments *comments;
    opus_int16 pcm[FRAME_SIZE * CHANNELS];
    int error = 0;
    int ret;
    int frame;
    unsigned char *data = NULL;
    long size;
    const char *path = "libopusenc-consumer.opus";

    comments = ope_comments_create();
    if (comments == NULL) {
        fail("ope_comments_create failed");
    }
    if (ope_comments_add(comments, "TITLE", "libopusenc conan consumer test") != OPE_OK) {
        fail("ope_comments_add failed");
    }

    enc = ope_encoder_create_file(path, comments, SAMPLE_RATE, CHANNELS, 0, &error);
    if (enc == NULL || error != OPE_OK) {
        fail(ope_strerror(error));
    }

    /* Deterministic serial number and fixed decision delay for reproducibility. */
    if (ope_encoder_ctl(enc, OPE_SET_SERIALNO(0x12345678)) != OPE_OK) {
        fail("OPE_SET_SERIALNO failed");
    }

    for (frame = 0; frame < FRAMES; frame++) {
        fill_pcm(pcm, frame);
        ret = ope_encoder_write(enc, pcm, FRAME_SIZE);
        if (ret != OPE_OK) {
            fail(ope_strerror(ret));
        }
    }

    ret = ope_encoder_drain(enc);
    if (ret != OPE_OK) {
        fail(ope_strerror(ret));
    }
    ope_encoder_destroy(enc);
    ope_comments_destroy(comments);

    size = read_entire_file(path, &data);
    check_ogg_structure(data, size);
    free(data);
    if (remove(path) != 0) {
        fail("cleanup failed");
    }

    printf("PASS libopusenc consumer encoded %d frames (%ld samples/channel), %ld bytes\n",
           FRAMES, (long)(FRAMES * FRAME_SIZE), size);
    return 0;
}
