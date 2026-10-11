/*
 * Consumer-side test for the packaged minimp3 library (Conan L1).
 *
 * Verifies real decoding behaviour of the packaged static library using a
 * synthetic MPEG1 Layer3 "digital silence" frame (header bytes
 * 0xFF 0xFB 0x90 0x00 + all-zero payload; frame length 417 bytes
 * = 144 * 128000 / 44100):
 *
 *   A. frame header parsing + one-frame decode (1152 samples, silence)
 *   B. truncated-frame handling
 *   C. buffer-mode API contracts (detect, NULL/oversize parameter guards)
 *   D. whole-buffer load API (mp3dec_load_buf)
 *   E. streaming API (mp3dec_ex_open_buf / mp3dec_ex_read) over 2 frames
 *   F. parameter-error contracts of the extended API
 *
 * All assertion anchors below were verified against the upstream
 * reference implementation on OHOS aarch64 (clang -std=c99).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "minimp3_ex.h"

static int checks_total = 0;
static int checks_failed = 0;

#define CHECK(cond) do { \
    checks_total++; \
    if (!(cond)) { \
        checks_failed++; \
        printf("FAILED line %d: %s\n", __LINE__, #cond); \
    } \
} while (0)

/* MPEG1 Layer3, 128 kbps, 44.1 kHz, stereo, no padding, no private bit.
 * Zeroed main_data decodes to digital silence. */
static void make_silence_frame(unsigned char *frame, size_t n)
{
    memset(frame, 0, n);
    frame[0] = 0xFF;
    frame[1] = 0xFB;
    frame[2] = 0x90;
    frame[3] = 0x00;
}

static long pcm_peak(const mp3d_sample_t *pcm, size_t n)
{
    long peak = 0;
    size_t i;
    for (i = 0; i < n; i++) {
        long v = pcm[i] < 0 ? -(long)pcm[i] : (long)pcm[i];
        if (v > peak)
            peak = v;
    }
    return peak;
}

int main(void)
{
    unsigned char frame[2 * 417];
    mp3d_sample_t pcm[2 * 1152 * 2];

    /* ---- A. frame header parsing + one-frame decode ---- */
    {
        mp3dec_t dec;
        mp3dec_frame_info_t info;
        int samples;
        make_silence_frame(frame, 417);
        mp3dec_init(&dec);
        memset(&info, 0, sizeof(info));
        samples = mp3dec_decode_frame(&dec, frame, 417, pcm, &info);
        CHECK(samples == 1152);          /* MPEG1 L3 granule payload   */
        CHECK(info.frame_bytes == 417);   /* 144*128000/44100           */
        CHECK(info.hz == 44100);          /* sample rate from header    */
        CHECK(info.channels == 2);        /* stereo channel mode        */
        CHECK(info.layer == 3);           /* Layer III                  */
        CHECK(pcm_peak(pcm, (size_t)samples * 2) == 0); /* silence     */
    }

    /* ---- B. truncated frame: header only, no full frame body ---- */
    {
        mp3dec_t dec;
        mp3dec_frame_info_t info;
        int samples;
        mp3dec_init(&dec);
        memset(&info, 0, sizeof(info));
        samples = mp3dec_decode_frame(&dec, frame, 4, pcm, &info);
        CHECK(samples == 0);              /* cannot decode partial data */
        CHECK(info.frame_bytes == 4);     /* header size only           */
    }

    /* ---- C. detect API + parameter guards ---- */
    {
        CHECK(mp3dec_detect_buf(frame, 417) == 0);            /* valid  */
        CHECK(mp3dec_detect_buf(NULL, 417) == MP3D_E_PARAM);  /* null   */
        CHECK(mp3dec_detect_buf(frame, (size_t)-1) == MP3D_E_PARAM);
    }

    /* ---- D. whole-buffer load API ---- */
    {
        mp3dec_t dec;
        mp3dec_file_info_t finfo;
        int ret;
        mp3dec_init(&dec);
        memset(&finfo, 0, sizeof(finfo));
        ret = mp3dec_load_buf(&dec, frame, 417, &finfo, NULL, NULL);
        CHECK(ret == 0);                        /* success              */
        CHECK(finfo.samples == 2304);           /* 1152 samples * 2 ch  */
        CHECK(finfo.hz == 44100);
        CHECK(finfo.avg_bitrate_kbps == 128);
        free(finfo.buffer);
        CHECK(mp3dec_load_buf(NULL, frame, 417, &finfo, NULL, NULL)
              == MP3D_E_PARAM);                 /* null decoder guard   */
    }

    /* ---- E. streaming API over two concatenated frames ---- */
    {
        mp3dec_ex_t dec;
        size_t n;
        int ret;
        make_silence_frame(frame, sizeof(frame));
        make_silence_frame(frame + 417, 417);
        memset(&dec, 0, sizeof(dec));
        ret = mp3dec_ex_open_buf(&dec, frame, sizeof(frame), 0);
        CHECK(ret == 0);                        /* opened               */
        CHECK(dec.samples == 4608);             /* 2 frames * 2304      */
        CHECK(dec.info.hz == 44100);
        memset(pcm, 0xAA, sizeof(pcm));
        n = mp3dec_ex_read(&dec, pcm, 1152);
        CHECK(n == 1152);                       /* first frame          */
        CHECK(pcm_peak(pcm, n) == 0);           /* silence              */
        n = mp3dec_ex_read(&dec, pcm, 2304);
        CHECK(n == 2304);                       /* second frame         */
        mp3dec_ex_close(&dec);
    }

    /* ---- F. parameter-error contracts of the extended API ---- */
    {
        mp3dec_io_t io;
        CHECK(mp3dec_ex_open_buf(NULL, frame, sizeof(frame), 0) == MP3D_E_PARAM);
        memset(&io, 0, sizeof(io));
        CHECK(mp3dec_detect_cb(&io, frame, sizeof(frame)) == MP3D_E_PARAM);
        CHECK(mp3dec_iterate_buf(frame, sizeof(frame), NULL, NULL)
              == MP3D_E_PARAM);
    }

    if (checks_failed) {
        printf("test_minimp3: FAIL (%d/%d assertions failed)\n",
               checks_failed, checks_total);
        return 1;
    }
    printf("test_minimp3: PASS (%d assertions passed)\n", checks_total);
    return 0;
}
