/*
Consumer test — dr_flac 0.12.39.

Builds a C program that consumes the real dr_flac package (include path +
DR_FLAC_IMPLEMENTATION in exactly one TU) and decodes a deterministic,
structurally-valid 2-channel FLAC test vector embedded in
flac_test_vector.h. It exercises two distinct dr_flac subframe decoders
(CONSTANT on channel 0, VERBATIM on channel 1) plus the multi-channel
independent path and the frame CRC-8 / CRC-16 verification, then asserts:

  - dr_flac reports version 0.12.39
  - STREAMINFO is recovered: 2 channels / 44100 Hz / 16 bps / 256 frames
  - channel 0 (CONSTANT) decodes to the expected constant for all 256 frames
  - channel 1 (VERBATIM) decodes to the exact sawtooth for all 256 frames

Every failed assertion sets a global and the process returns non-zero, so the
conan test() step (which runs the binary) fails the build. No audio device is
opened — decoding is from an in-memory buffer only.

DR_FLAC_IMPLEMENTATION is defined once in CMakeLists.txt (target_compile_definitions)
so the implementation compiles into exactly this translation unit.
*/
#include <dr_flac/dr_flac.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "flac_test_vector.h"

static int g_fail = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s\n", (msg)); g_fail = 1; } else { printf("ok  : %s\n", (msg)); } } while (0)

typedef struct { unsigned int off; } vec_state;

static size_t on_read(void* ud, void* out, size_t n) {
    unsigned char* buf = (unsigned char*)out;
    vec_state* st = (vec_state*)ud;
    size_t avail = (g_testFlacSize > st->off) ? (g_testFlacSize - st->off) : 0;
    if (n > avail) n = avail;
    memcpy(buf, g_testFlac + st->off, n);
    st->off = (unsigned int)(st->off + n);
    return n;
}

static drflac_bool32 on_seek(void* ud, int offset, drflac_seek_origin origin) {
    vec_state* st = (vec_state*)ud;
    if (origin == drflac_seek_origin_start) {
        st->off = (unsigned int)offset;
    } else if (origin == drflac_seek_origin_current) {
        st->off = (unsigned int)((int)st->off + offset);
    } else {
        st->off = g_testFlacSize - (unsigned int)offset;
    }
    if (st->off > g_testFlacSize) st->off = g_testFlacSize;
    return DRFLAC_TRUE;
}

int main(void) {
    drflac_uint32 maj = 0, min = 0, rev = 0;
    drflac_version(&maj, &min, &rev);
    printf("dr_flac %u.%u.%u (string=%s)\n", maj, min, rev, drflac_version_string());
    CHECK(maj == 0 && min == 12 && rev == 39, "version is 0.12.39");

    vec_state st; st.off = 0;
    drflac* f = drflac_open(on_read, on_seek, &st, NULL);
    if (!f) { printf("OPEN FAILED\n"); return 2; }
    printf("opened: ch=%u rate=%u bps=%u frames=%llu maxblk=%u\n",
        (unsigned)f->channels, (unsigned)f->sampleRate, (unsigned)f->bitsPerSample,
        (unsigned long long)f->totalPCMFrameCount, (unsigned)f->maxBlockSizeInPCMFrames);

    CHECK(f->channels == 2, "channels==2");
    CHECK(f->sampleRate == 44100, "sampleRate==44100");
    CHECK(f->bitsPerSample == 16, "bitsPerSample==16");
    CHECK(f->totalPCMFrameCount == g_testFrames, "totalPCMFrameCount==256");

    drflac_int16 out[g_testFrames * 2];
    drflac_uint64 got = drflac_read_pcm_frames_s16(f, g_testFrames, out);
    printf("read %llu/%u frames\n", (unsigned long long)got, (unsigned)g_testFrames);
    CHECK(got == g_testFrames, "read all 256 frames");

    int c0ok = 1, c1ok = 1;
    for (unsigned i = 0; i < g_testFrames; i++) {
        int l = out[2 * i], r = out[2 * i + 1];
        if (l != g_testConstant0) { if (c0ok) printf("  ch0 mismatch @%u got=%d want=%d\n", i, l, g_testConstant0); c0ok = 0; }
        int v = (i * 128) % 32768;
        int expect = (v >= 16384) ? (v - 32768) : v;
        if (r != expect) { if (c1ok) printf("  ch1 mismatch @%u got=%d want=%d\n", i, r, expect); c1ok = 0; }
    }
    CHECK(c0ok, "ch0 CONSTANT == C0 for all 256 frames");
    CHECK(c1ok, "ch1 VERBATIM sawtooth matches for all 256 frames");

    printf("frame[0] L=%d R=%d | frame[128] L=%d R=%d\n", out[0], out[1], out[256], out[257]);
    drflac_close(f);
    printf(g_fail ? "TEST: FAILED\n" : "TEST: ALL PASS\n");
    return g_fail ? 1 : 0;
}
