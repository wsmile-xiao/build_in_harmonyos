/* test_libmpcdec.c — consumer test for the packaged libmpcdec.
 *
 * Exercises the real public decoder API of the installed static library:
 *   mpc_reader (in-memory callbacks)
 *     -> mpc_demux_init -> mpc_demux_get_info
 *     -> mpc_demux_decode over every SV8 frame
 *
 * The input is a genuine MusePack SV8 stream embedded as a byte array
 * (test_package/fixture_mpc.h, produced by the reference mpcenc of the same
 * upstream release from a synthetic stereo WAV).  Both the parsed stream
 * header and the decoded PCM are asserted, so the test fails if the packaged
 * library is missing, stale, miscompiled, or has a broken decoder path.
 */
#include <math.h>
#include <stdio.h>
#include <string.h>

#include <mpc/mpcdec.h>
#include <mpc/reader.h>
#include <mpc/streaminfo.h>

#include "fixture_mpc.h"

/* Stream facts of the embedded fixture (see fixture_mpc.h provenance). */
#define EXPECT_RATE     44100u
#define EXPECT_CHANNELS 2u
#define EXPECT_SAMPLES  6615ULL
#define EXPECT_FRAMES   7

/* Reference PCM head (first interleaved float samples) decoded from the same
 * fixture by the reference mpcdec of the same release. */
static const double expected_head[8] = {
    0.001197, 0.001485, 0.021853, 0.024398,
    0.046692, 0.052337, 0.067865, 0.075863
};

typedef struct {
    const unsigned char *data;
    size_t size;
    size_t pos;
} mem_stream;

static mpc_int32_t mem_read(mpc_reader *r, void *ptr, mpc_int32_t size)
{
    mem_stream *m = (mem_stream *)r->data;
    size_t avail = m->size - m->pos;
    if ((size_t)size > avail)
        size = (mpc_int32_t)avail;
    memcpy(ptr, m->data + m->pos, (size_t)size);
    m->pos += (size_t)size;
    return size;
}

static mpc_bool_t mem_seek(mpc_reader *r, mpc_int32_t offset)
{
    mem_stream *m = (mem_stream *)r->data;
    if (offset < 0 || (size_t)offset > m->size)
        return MPC_FALSE;
    m->pos = (size_t)offset;
    return MPC_TRUE;
}

static mpc_int32_t mem_tell(mpc_reader *r)
{
    return (mpc_int32_t)((mem_stream *)r->data)->pos;
}

static mpc_int32_t mem_get_size(mpc_reader *r)
{
    return (mpc_int32_t)((mem_stream *)r->data)->size;
}

static mpc_bool_t mem_canseek(mpc_reader *r)
{
    (void)r;
    return MPC_TRUE;
}

int main(void)
{
    mem_stream ms = { fixture_mpc, (size_t)fixture_mpc_len, 0 };
    mpc_reader reader;

    reader.read = mem_read;
    reader.seek = mem_seek;
    reader.tell = mem_tell;
    reader.get_size = mem_get_size;
    reader.canseek = mem_canseek;
    reader.data = &ms;

    mpc_demux *demux = mpc_demux_init(&reader);
    if (demux == NULL) {
        fputs("FAIL: mpc_demux_init on embedded SV8 stream\n", stderr);
        return 1;
    }

    mpc_streaminfo si;
    mpc_demux_get_info(demux, &si);
    printf("stream: SV%u %u Hz %u ch %llu samples\n", si.stream_version,
           si.sample_freq, si.channels, (unsigned long long)si.samples);

    if (si.stream_version != 8) {
        fprintf(stderr, "FAIL: expected SV8, got SV%u\n", si.stream_version);
        mpc_demux_exit(demux);
        return 2;
    }
    if (si.sample_freq != EXPECT_RATE || si.channels != EXPECT_CHANNELS ||
        si.samples != EXPECT_SAMPLES) {
        fprintf(stderr, "FAIL: unexpected streaminfo (%u Hz, %u ch, %llu samples)\n",
                si.sample_freq, si.channels, (unsigned long long)si.samples);
        mpc_demux_exit(demux);
        return 3;
    }

    static MPC_SAMPLE_FORMAT sample_buffer[MPC_DECODER_BUFFER_LENGTH];
    unsigned long long total_samples = 0;
    double sum_squares = 0.0;
    double peak = 0.0;
    double head[8] = { 0.0 };
    unsigned head_filled = 0;
    int frames = 0;

    for (;;) {
        mpc_frame_info frame;
        memset(&frame, 0, sizeof frame);
        frame.buffer = sample_buffer;

        if (mpc_demux_decode(demux, &frame) != MPC_STATUS_OK) {
            fputs("FAIL: mpc_demux_decode returned an error\n", stderr);
            mpc_demux_exit(demux);
            return 4;
        }
        if (frame.bits == -1)          /* end of stream */
            break;
        if (frame.samples == 0) {
            fputs("FAIL: decoded an empty audio frame\n", stderr);
            mpc_demux_exit(demux);
            return 5;
        }

        unsigned long n = (unsigned long)frame.samples * si.channels;
        for (unsigned long i = 0; i < n; i++) {
            double v = (double)sample_buffer[i];
            if (head_filled < 8) {
                head[head_filled] = v;
                head_filled++;
            }
            sum_squares += v * v;
            if (fabs(v) > peak)
                peak = fabs(v);
        }
        total_samples += frame.samples;
        frames++;
        if (frames > 1000) {
            fputs("FAIL: decode did not reach end of stream\n", stderr);
            mpc_demux_exit(demux);
            return 6;
        }
    }
    mpc_demux_exit(demux);

    double rms = sqrt(sum_squares / ((double)total_samples * (double)si.channels));
    printf("decoded %d frames / %llu samples, rms=%.6f peak=%.6f\n",
           frames, total_samples, rms, peak);
    printf("first samples: %.6f %.6f %.6f %.6f\n",
           head[0], head[1], head[2], head[3]);

    if (total_samples != EXPECT_SAMPLES || frames != EXPECT_FRAMES) {
        fprintf(stderr, "FAIL: decoded %d frames / %llu samples, expected %d / %llu\n",
                frames, total_samples, EXPECT_FRAMES, EXPECT_SAMPLES);
        return 7;
    }
    /* Lossy codec: allow a small tolerance around the reference values. */
    for (unsigned i = 0; i < 8; i++) {
        if (fabs(head[i] - expected_head[i]) > 0.01) {
            fprintf(stderr, "FAIL: sample %u = %.6f, expected %.6f\n",
                    i, head[i], expected_head[i]);
            return 8;
        }
    }
    if (rms < 0.18 || rms > 0.28) {
        fprintf(stderr, "FAIL: implausible RMS %.6f (expected ~0.229)\n", rms);
        return 9;
    }
    if (peak < 0.30 || peak > 0.43) {
        fprintf(stderr, "FAIL: implausible peak %.6f (expected ~0.366)\n", peak);
        return 10;
    }

    puts("libmpcdec decode test: OK (SV8 header + 7 frames / 6615 samples verified)");
    return 0;
}
