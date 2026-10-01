/* sndfile_stub.c — minimal RIFF/WAVE PCM reader behind the shim header.
 *
 * Parses the fmt + data chunks, supports WAVE_FORMAT_PCM (1) and
 * WAVE_FORMAT_EXTENSIBLE (0xFFFE, real format in SubFormat GUID first
 * two bytes) with 16/24/32-bit PCM samples, converts samples to double
 * in [-1, 1) exactly the way libsndfile does for PCM.
 */
#include "sndfile.h"

#include <stdlib.h>
#include <string.h>

static uint16_t rd16(const uint8_t *p) {
    return (uint16_t)(p[0] | (p[1] << 8));
}

static uint32_t rd32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

SNDFILE *sf_open(const char *path, int mode, SF_INFO *sfinfo) {
    SF_FILE *sf;
    uint8_t hdr[12];
    int fmt_seen = 0, data_seen = 0;
    uint16_t audio_format = 0, channels = 0, bits = 0;
    uint32_t samplerate = 0, data_bytes = 0, data_off = 0;

    (void)mode;
    if (!path || !sfinfo)
        return NULL;
    memset(sfinfo, 0, sizeof(*sfinfo));

    FILE *fp = fopen(path, "rb");
    if (!fp)
        return NULL;
    if (fread(hdr, 1, 12, fp) != 12 || memcmp(hdr, "RIFF", 4) != 0 || memcmp(hdr + 8, "WAVE", 4) != 0) {
        fclose(fp);
        return NULL;
    }

    for (;;) {
        uint8_t ch[8];
        if (fread(ch, 1, 8, fp) != 8)
            break;
        uint32_t size = rd32(ch + 4);
        if (memcmp(ch, "fmt ", 4) == 0) {
            uint8_t f[40];
            uint32_t want = size < 40 ? size : 40;
            if (want < 16 || fread(f, 1, want, fp) != want) {
                fclose(fp);
                return NULL;
            }
            if (size > want) /* skip any extra fmt bytes */
                fseek(fp, (long)(size - want), SEEK_CUR);
            audio_format = rd16(f);
            channels = rd16(f + 2);
            samplerate = rd32(f + 4);
            bits = rd16(f + 14);
            if (audio_format == 0xFFFE && want >= 40) {
                audio_format = rd16(f + 24); /* SubFormat GUID first 2 bytes */
            }
            fmt_seen = 1;
        } else if (memcmp(ch, "data", 4) == 0) {
            data_bytes = size;
            data_off = (uint32_t)ftell(fp);
            data_seen = 1;
            fseek(fp, (long)size, SEEK_CUR); /* keep scanning for a later fmt */
        } else {
            fseek(fp, (long)size, SEEK_CUR);
        }
        if (size & 1)
            fseek(fp, 1, SEEK_CUR); /* RIFF chunks are word-aligned */
    }

    if (!fmt_seen || !data_seen || channels == 0 || bits < 16 || bits > 32 ||
        (audio_format != 1) || data_bytes % channels != 0) {
        fclose(fp);
        return NULL;
    }

    sf = (SF_FILE *)calloc(1, sizeof(*sf));
    if (!sf) {
        fclose(fp);
        return NULL;
    }
    sf->fp = fp;
    sf->channels = channels;
    sf->samplerate = (int)samplerate;
    sf->bits_per_sample = bits;
    sf->data_bytes = data_bytes;
    sf->data_offset = data_off;
    sf->pos_bytes = 0;
    if (0 != fseek(fp, (long)data_off, SEEK_SET)) {
        free(sf);
        fclose(fp);
        return NULL;
    }

    int bytes_per_frame = channels * (bits / 8);
    sfinfo->frames = (int)(data_bytes / bytes_per_frame);
    sfinfo->samplerate = (int)samplerate;
    sfinfo->channels = channels;
    sfinfo->format = SF_FORMAT_WAV | (bits == 16 ? SF_FORMAT_PCM_16
                                    : bits == 24 ? SF_FORMAT_PCM_24
                                                 : SF_FORMAT_PCM_32);
    sfinfo->sections = 1;
    sfinfo->seekable = 1;
    return sf;
}

sf_count_t sf_readf_double(SNDFILE *sf, double *data, sf_count_t frames) {
    if (!sf || !data || frames <= 0)
        return 0;
    int bps = sf->bits_per_sample / 8;
    int bpf = sf->channels * bps;
    sf_count_t want_frames = frames;
    uint32_t remaining = (sf->data_bytes - sf->pos_bytes) / bpf;
    if ((uint32_t)want_frames > remaining)
        want_frames = remaining;
    if (want_frames <= 0)
        return 0;

    uint8_t *raw = (uint8_t *)malloc((size_t)(want_frames * bpf));
    if (!raw)
        return 0;
    size_t got = fread(raw, 1, (size_t)(want_frames * bpf), sf->fp);
    if (got != (size_t)(want_frames * bpf)) {
        free(raw);
        return 0;
    }
    sf->pos_bytes += (uint32_t)got;

    for (sf_count_t f = 0; f < want_frames; ++f) {
        for (int c = 0; c < sf->channels; ++c) {
            const uint8_t *p = raw + f * bpf + c * bps;
            int64_t v = 0;
            if (bps == 2) {
                int16_t s = (int16_t)(p[0] | (p[1] << 8));
                v = s;
            } else if (bps == 3) {
                v = (int32_t)p[0] | ((int32_t)p[1] << 8) | ((int32_t)p[2] << 16);
                if (v & 0x800000)
                    v -= 0x1000000;
            } else {
                v = (int32_t)(((uint32_t)p[0]) | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24));
            }
            data[f * sf->channels + c] = (double)v / (bps == 2 ? 32768.0 : bps == 3 ? 8388608.0 : 2147483648.0);
        }
    }
    free(raw);
    return want_frames;
}

int sf_close(SNDFILE *sf) {
    if (!sf)
        return 1;
    int rc = fclose(sf->fp);
    free(sf);
    return rc;
}
