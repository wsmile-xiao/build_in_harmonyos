#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <opus/opus.h>
#include <opus/opusenc.h>

static void fail(const char *message)
{
    fprintf(stderr, "FAIL libopusenc consumer: %s\n", message);
    exit(1);
}

int main(void)
{
    OggOpusEnc *enc;
    OggOpusComments *comments;
    int error;
    const char *filename = "libopusenc_consumer.opus";
    FILE *check;
    long filesize;
    unsigned char magic[4];

    comments = ope_comments_create();
    if (!comments) {
        fail("ope_comments_create failed");
    }
    ope_comments_add(comments, "ARTIST", "Test");
    ope_comments_add(comments, "TITLE", "libopusenc test");

    enc = ope_encoder_create_file(filename, comments, 48000, 1, 0, &error);
    if (!enc || error != OPE_OK) {
        fprintf(stderr, "ope_encoder_create_file failed: %s\n", ope_strerror(error));
        ope_comments_destroy(comments);
        fail("encoder creation failed");
    }

    /* Write 1 second of silence (48000 Hz, 1 channel, 16-bit) */
    /* Write in 960-sample frames (20ms at 48kHz) */
    short silence[960];
    memset(silence, 0, sizeof(silence));
    for (int i = 0; i < 50; i++) {
        int ret = ope_encoder_write(enc, silence, 960);
        if (ret != OPE_OK) {
            ope_encoder_destroy(enc);
            ope_comments_destroy(comments);
            fail("ope_encoder_write failed");
        }
    }

    ope_encoder_drain(enc);
    ope_encoder_destroy(enc);
    ope_comments_destroy(comments);

    /* Verify the output file */
    check = fopen(filename, "rb");
    if (!check) {
        fail("output file not created");
    }

    fseek(check, 0, SEEK_END);
    filesize = ftell(check);
    fseek(check, 0, SEEK_SET);

    if (filesize <= 0) {
        fclose(check);
        fail("output file is empty");
    }

    /* Check OggS magic number at the start */
    if (fread(magic, 1, 4, check) != 4 || memcmp(magic, "OggS", 4) != 0) {
        fclose(check);
        fail("output file is not a valid Ogg file");
    }
    fclose(check);

    /* Clean up */
    if (remove(filename) != 0) {
        fprintf(stderr, "WARN: cleanup of %s failed\n", filename);
    }

    printf("PASS libopusenc consumer filesize=%ld\n", filesize);
    return 0;
}
