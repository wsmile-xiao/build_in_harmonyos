/* sndfile.h — minimal libsndfile-compatible shim (test-only).
 *
 * Implements exactly the API surface used by libebur128's upstream test
 * programs (test/tests.c, test/minimal-example.c): sf_open / sf_readf_double
 * / sf_close over SF_INFO. Supports RIFF WAVE PCM (16/24/32-bit) and
 * WAVE_FORMAT_EXTENSIBLE multi-channel files — enough to feed the EBU R128
 * test vectors. This is a test harness, NOT a libsndfile adaptation (which
 * would be a separate package/PR).
 */
#ifndef SNDFILE_STUB_H
#define SNDFILE_STUB_H

#include <stdint.h>
#include <stdio.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SFM_READ 0x10

enum {
    SF_FORMAT_WAV = 0x010000,
    SF_FORMAT_PCM_16 = 0x0002,
    SF_FORMAT_PCM_24 = 0x0003,
    SF_FORMAT_PCM_32 = 0x0004,
    SF_FORMAT_FLOAT = 0x0005,
};

typedef int64_t sf_count_t;

typedef struct {
    int frames;
    int samplerate;
    int channels;
    int format;
    int sections;
    int seekable;
} SF_INFO;

typedef struct sndfile_stub SF_FILE;
#define SNDFILE SF_FILE

struct sndfile_stub {
    FILE *fp;
    int channels;
    int samplerate;
    int bits_per_sample;
    uint32_t data_bytes;
    uint32_t data_offset;
    uint32_t pos_bytes;
};

SNDFILE *sf_open(const char *path, int mode, SF_INFO *sfinfo);
sf_count_t sf_readf_double(SNDFILE *sndfile, double *data, sf_count_t frames);
int sf_close(SNDFILE *sndfile);

#ifdef __cplusplus
}
#endif

#endif /* SNDFILE_STUB_H */
