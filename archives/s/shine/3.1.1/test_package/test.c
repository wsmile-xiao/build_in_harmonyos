#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <shine/layer3.h>

/* Consumer-style test: uses only the installed public header <shine/layer3.h>
 * and the libshine API. Generates a short mono PCM sine sweep, encodes it to
 * MP3 frames via the public API and verifies the observable result: an MP3
 * frame with a valid 11-bit sync word (0xFFE) is produced, the encoded output
 * is non-silent (discriminating real audio from digital zero), and the
 * configuration helpers reject unsupported parameters. */
int main(void) {
    shine_config_t config;
    shine_t s;

    /* --- config helpers (public API) --- */
    shine_set_config_mpeg_defaults(&config.mpeg);
    config.wave.channels = PCM_MONO;
    config.wave.samplerate = 44100;
    config.mpeg.bitr = 128;

    if (shine_check_config(config.wave.samplerate, config.mpeg.bitr) < 0) {
        fprintf(stderr, "FAIL: shine_check_config rejected 44100Hz/128kbit\n");
        return 1;
    }
    /* 44100Hz is MPEG-I, where the minimum bitrate is 32kbit */
    if (shine_check_config(44100, 32) < 0) {
        fprintf(stderr, "FAIL: shine_check_config rejected 44100Hz/32kbit (MPEG-I minimum)\n");
        return 2;
    }
    /* 8kbit only exists for MPEG-II/MPEG-2.5, not MPEG-I: must be rejected */
    if (shine_check_config(44100, 8) >= 0) {
        fprintf(stderr, "FAIL: shine_check_config accepted 8kbit at 44100Hz (invalid for MPEG-I)\n");
        return 11;
    }
    /* unsupported samplerate must be rejected */
    if (shine_check_config(12345, 128) >= 0) {
        fprintf(stderr, "FAIL: shine_check_config accepted bogus samplerate 12345\n");
        return 3;
    }
    if (shine_find_bitrate_index(128, MPEG_I) < 0) {
        fprintf(stderr, "FAIL: shine_find_bitrate_index rejected 128kbit MPEG-I\n");
        return 4;
    }

    /* --- initialise encoder --- */
    s = shine_initialise(&config);
    if (!s) {
        fprintf(stderr, "FAIL: shine_initialise returned NULL\n");
        return 5;
    }

    int samples_per_pass = shine_samples_per_pass(s);
    if (samples_per_pass <= 0) {
        fprintf(stderr, "FAIL: shine_samples_per_pass = %d\n", samples_per_pass);
        shine_close(s);
        return 6;
    }

    /* --- encode a short sine sweep (mono) --- */
    int passes = 4;
    unsigned long total_written = 0;
    long long pcm_energy = 0;   /* sum of |sample| across all passes */
    long encoded_nonzero = 0;   /* non-zero encoded payload bytes */
    for (int p = 0; p < passes; p++) {
        int16_t buf[SHINE_MAX_SAMPLES];
        for (int i = 0; i < samples_per_pass; i++) {
            double t = (double)(p * samples_per_pass + i) / 44100.0;
            buf[i] = (int16_t)(3000.0 * sin(2.0 * 3.14159265 * 440.0 * t));
            pcm_energy += (buf[i] < 0) ? -(long long)buf[i] : (long long)buf[i];
        }
        /* shine_encode_buffer takes an array of per-channel sample pointers */
        int16_t *chans[1] = { buf };
        int written = 0;
        unsigned char *mp3 = shine_encode_buffer(s, chans, &written);
        if (written > 0) {
            if (mp3 == NULL) {
                fprintf(stderr, "FAIL: written>0 but mp3==NULL\n");
                shine_close(s);
                return 7;
            }
            /* verify the first two bytes are an MPEG sync word 0xFFE */
            if (p == 0 && (mp3[0] != 0xFF || (mp3[1] & 0xE0) != 0xE0)) {
                fprintf(stderr, "FAIL: first MP3 frame has no 0xFFE sync word (%02x %02x)\n",
                        mp3[0], mp3[1]);
                shine_close(s);
                return 8;
            }
            /* discriminative check: encoded payload must not be digital zero
             * (a silent input would produce near-zero payload bytes); count
             * non-zero bytes across the encoded output */
            for (int k = 4; k < written; k++) {
                if (mp3[k] != 0) encoded_nonzero++;
            }
            total_written += (unsigned long)written;
        }
    }

    /* --- flush --- */
    int written = 0;
    unsigned char *tail = shine_flush(s, &written);
    if (written < 0) {
        fprintf(stderr, "FAIL: shine_flush returned negative written size\n");
        shine_close(s);
        return 9;
    }
    total_written += (unsigned long)written;

    shine_close(s);

    if (total_written < 4 * 64) {
        fprintf(stderr, "FAIL: encoded too little data (%lu bytes)\n", total_written);
        return 10;
    }

    /* discriminative assertions: non-silent input produced non-trivial output */
    if (pcm_energy == 0) {
        fprintf(stderr, "FAIL: generated PCM is digital silence (pcm_energy=0)\n");
        return 12;
    }
    if (encoded_nonzero == 0) {
        fprintf(stderr, "FAIL: encoded MP3 payload is all-zero (non-silence lost)\n");
        return 13;
    }

    printf("shine consumer test OK: %lu bytes MP3 encoded, pcm_energy=%lld, "
           "encoded_nonzero=%ld, API assertions passed\n",
           total_written, pcm_energy, encoded_nonzero);
    return 0;
}
